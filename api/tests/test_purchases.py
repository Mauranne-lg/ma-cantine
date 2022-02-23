from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from data.factories import UserFactory, PurchaseFactory, CanteenFactory
from data.models import Purchase
from .utils import authenticate


class TestPurchaseApi(APITestCase):
    def test_get_purchases_unauthenticated(self):
        """
        This endpoint is only available when authenticated
        """
        response = self.client.get(reverse("purchase_list_create"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_get_someone_elses_purchases(self):
        """
        This endpoint can only return the purchases of canteens the logged user manages
        """
        other_user = UserFactory.create()
        other_user_canteen = CanteenFactory.create()
        other_user_canteen.managers.add(other_user)

        PurchaseFactory.create(canteen=other_user_canteen)

        response = self.client.get(reverse("purchase_list_create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json().get("results", [])
        self.assertEqual(len(body), 0)

    @authenticate
    def test_get_purchases(self):
        """
        The logged user should get the purchases that concern them
        """
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)

        PurchaseFactory.create(canteen=canteen)
        PurchaseFactory.create(canteen=canteen)

        response = self.client.get(reverse("purchase_list_create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json().get("results", [])
        self.assertEqual(len(body), 2)

    def test_create_purchase_unauthenticated(self):
        """
        The purchase creation is only available when logged in
        """
        payload = {
            "date": "2022-01-13",
            "canteen_id": 1,
            "description": "Saumon",
            "provider": "Test provider",
            "category": "PRODUITS_DE_LA_MER",
            "characteristic": ["BIO"],
            "price_ht": 15.23,
        }
        response = self.client.post(reverse("purchase_list_create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_create_purchase_someone_elses_canteen(self):
        """
        A user can only create a purchase of a canteen they manage
        """
        other_user = UserFactory.create()
        other_user_canteen = CanteenFactory.create()
        other_user_canteen.managers.add(other_user)

        payload = {
            "date": "2022-01-13",
            "canteen": other_user_canteen.id,
            "description": "Saumon",
            "provider": "Test provider",
            "category": "PRODUITS_DE_LA_MER",
            "characteristic": ["BIO"],
            "price_ht": 15.23,
        }
        response = self.client.post(reverse("purchase_list_create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_create_purchase(self):
        """
        A user can create a purchase
        """
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        payload = {
            "date": "2022-01-13",
            "canteen": canteen.id,
            "description": "Saumon",
            "provider": "Test provider",
            "category": "PRODUITS_DE_LA_MER",
            "characteristic": ["BIO"],
            "price_ht": 15.23,
        }
        response = self.client.post(reverse("purchase_list_create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @authenticate
    def test_create_purchase_nonexistent_canteen(self):
        """
        A user cannot create a purchase for an nonexistent canteen
        """
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        payload = {
            "date": "2022-01-13",
            "canteen": "999",
            "description": "Saumon",
            "provider": "Test provider",
            "category": "PRODUITS_DE_LA_MER",
            "characteristic": ["BIO"],
            "price_ht": 15.23,
        }
        response = self.client.post(reverse("purchase_list_create"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_purchases_unauthenticated(self):
        """
        The purchase update is only available when logged in
        """
        purchase = PurchaseFactory.create()
        payload = {
            "id": purchase.id,
            "price_ht": 15.23,
        }
        response = self.client.patch(
            reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_update_purchase(self):
        """
        A user can update the data from a purchase object
        """
        purchase = PurchaseFactory.create()
        purchase.canteen.managers.add(authenticate.user)
        new_canteen = CanteenFactory.create()
        new_canteen.managers.add(authenticate.user)

        payload = {
            "id": purchase.id,
            "canteen": new_canteen.id,
            "description": "Saumon",
            "provider": "Test provider",
            "price_ht": 15.23,
        }

        response = self.client.patch(
            reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        purchase.refresh_from_db()
        self.assertEqual(purchase.canteen, new_canteen)
        self.assertEqual(purchase.description, "Saumon")
        self.assertEqual(purchase.provider, "Test provider")
        self.assertEqual(float(purchase.price_ht), 15.23)

    @authenticate
    def test_update_someone_elses_purchase(self):
        """
        A user should not be able to update someone else's purchase object
        """
        purchase = PurchaseFactory.create()

        payload = {
            "id": purchase.id,
            "description": "Saumon",
            "provider": "Test provider",
            "price_ht": 15.23,
        }

        response = self.client.patch(
            reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @authenticate
    def test_update_someone_elses_canteen(self):
        """
        A user should not be able to set someone else's canteen in a purchase update
        """
        purchase = PurchaseFactory.create()
        purchase.canteen.managers.add(authenticate.user)
        new_canteen = CanteenFactory.create()

        payload = {
            "id": purchase.id,
            "canteen": new_canteen.id,
        }

        response = self.client.patch(
            reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}), payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_purchase_total_summary(self):
        """
        Given a year, return spending by category
        Bio category is the sum of all products with either bio or bio en conversion labels
        Every category apart from bio should exlude bio (so bio + label rouge gets counted in bio but not label rouge)
        The category of AOC/AOP/IGP should count items with two or more labels once
        """
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        # For the year 2020
        # bio (+ rouge)
        PurchaseFactory.create(
            canteen=canteen,
            date="2020-01-01",
            characteristics=[Purchase.Characteristic.BIO, Purchase.Characteristic.LABEL_ROUGE],
            price_ht=50,
        )
        # bio en conversion (+ igp)
        PurchaseFactory.create(
            canteen=canteen,
            date="2020-08-01",
            characteristics=[Purchase.Characteristic.CONVERSION_BIO, Purchase.Characteristic.IGP],
            price_ht=150,
        )
        # hve x2 = 10
        PurchaseFactory.create(
            canteen=canteen, date="2020-01-01", characteristics=[Purchase.Characteristic.HVE], price_ht=2
        )
        PurchaseFactory.create(
            canteen=canteen, date="2020-01-01", characteristics=[Purchase.Characteristic.HVE], price_ht=8
        )
        # rouge x2 = 20
        PurchaseFactory.create(
            canteen=canteen, date="2020-01-01", characteristics=[Purchase.Characteristic.LABEL_ROUGE], price_ht=12
        )
        PurchaseFactory.create(
            canteen=canteen, date="2020-01-01", characteristics=[Purchase.Characteristic.LABEL_ROUGE], price_ht=8
        )
        # aoc, igp + igp = 30
        PurchaseFactory.create(
            canteen=canteen,
            date="2020-01-01",
            characteristics=[Purchase.Characteristic.AOCAOP, Purchase.Characteristic.IGP],
            price_ht=22,
        )
        PurchaseFactory.create(
            canteen=canteen, date="2020-01-01", characteristics=[Purchase.Characteristic.IGP], price_ht=8
        )
        # some other durable label
        PurchaseFactory.create(
            canteen=canteen, date="2020-01-08", characteristics=[Purchase.Characteristic.PECHE_DURABLE], price_ht=240
        )
        # no labels
        PurchaseFactory.create(canteen=canteen, date="2020-01-01", characteristics=[], price_ht=500)

        # Not in the year 2020 - smoke test for year filtering
        PurchaseFactory.create(
            canteen=canteen, date="2019-01-01", characteristics=[Purchase.Characteristic.BIO], price_ht=666
        )

        response = self.client.get(
            reverse("canteen_purchases_summary", kwargs={"canteen_pk": canteen.id}), {"year": 2020}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        body = response.json()
        self.assertEqual(body["total"], 1000.0)
        self.assertEqual(body["bio"], 200.0)
        self.assertEqual(body["sustainable"], 300.0)
        self.assertEqual(body["hve"], 10.0)
        self.assertEqual(body["rouge"], 20.0)
        self.assertEqual(body["aocAopIgp"], 30.0)

    def test_purchase_summary_unauthenticated(self):
        canteen = CanteenFactory.create()
        response = self.client.get(
            reverse("canteen_purchases_summary", kwargs={"canteen_pk": canteen.id}), {"year": 2020}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_purchase_not_authorized(self):
        canteen = CanteenFactory.create()
        response = self.client.get(
            reverse("canteen_purchases_summary", kwargs={"canteen_pk": canteen.id}), {"year": 2020}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @authenticate
    def test_purchase_missing_year(self):
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        response = self.client.get(
            reverse("canteen_purchases_summary", kwargs={"canteen_pk": canteen.id}),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @authenticate
    def test_purchase_inexistent_canteen(self):
        response = self.client.get(reverse("canteen_purchases_summary", kwargs={"canteen_pk": 999999}), {"year": 2020})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @authenticate
    def test_delete_purchase(self):
        """
        A user can delete a purchase object
        """
        purchase = PurchaseFactory.create()
        purchase.canteen.managers.add(authenticate.user)

        response = self.client.delete(reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(Purchase.objects.filter(pk=purchase.id).count(), 0)

    @authenticate
    def test_delete_unauthorized(self):
        """
        A user cannot delete a purchase object of a canteen they don't manage
        """
        purchase = PurchaseFactory.create()

        response = self.client.delete(reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(Purchase.objects.filter(pk=purchase.id).count(), 1)

    def test_delete_unauthenticated(self):
        """
        A user cannot delete a purchase object of a canteen if they're not authenticated
        """
        purchase = PurchaseFactory.create()

        response = self.client.delete(reverse("purchase_retrieve_update_destroy", kwargs={"pk": purchase.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(Purchase.objects.filter(pk=purchase.id).count(), 1)

    @authenticate
    def test_search_purchases(self):
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        PurchaseFactory.create(description="avoine", canteen=canteen)
        PurchaseFactory.create(description="tomates", canteen=canteen)
        PurchaseFactory.create(description="pommes", canteen=canteen)

        search_term = "avoine"
        response = self.client.get(f"{reverse('purchase_list_create')}?search={search_term}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].get("description"), "avoine")

    @authenticate
    def test_search_only_user_purchases(self):
        PurchaseFactory.create(description="avoine")
        PurchaseFactory.create(description="tomates")
        PurchaseFactory.create(description="pommes")

        search_term = "avoine"
        response = self.client.get(f"{reverse('purchase_list_create')}?search={search_term}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 0)

    @authenticate
    def test_filter_by_canteen(self):
        canteen = CanteenFactory.create()
        other_canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        other_canteen.managers.add(authenticate.user)
        PurchaseFactory.create(description="avoine", canteen=canteen)
        PurchaseFactory.create(description="tomates", canteen=other_canteen)
        PurchaseFactory.create(description="pommes", canteen=canteen)

        canteen_id = canteen.id
        response = self.client.get(f"{reverse('purchase_list_create')}?canteen__id={canteen_id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])

        self.assertEqual(len(results), 2)

    @authenticate
    def test_filter_by_characteristic(self):
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        PurchaseFactory.create(description="avoine", canteen=canteen, characteristics=[Purchase.Characteristic.BIO])
        PurchaseFactory.create(
            description="tomates",
            canteen=canteen,
            characteristics=[Purchase.Characteristic.BIO, Purchase.Characteristic.PECHE_DURABLE],
        )
        PurchaseFactory.create(
            description="pommes", canteen=canteen, characteristics=[Purchase.Characteristic.PECHE_DURABLE]
        )

        response = self.client.get(f"{reverse('purchase_list_create')}?characteristics={Purchase.Characteristic.BIO}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 2)

        response = self.client.get(
            f"{reverse('purchase_list_create')}?characteristics={Purchase.Characteristic.BIO}&characteristics={Purchase.Characteristic.PECHE_DURABLE}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 1)

    @authenticate
    def test_filter_by_category(self):
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        PurchaseFactory.create(description="avoine", canteen=canteen, category=Purchase.Category.PRODUITS_DE_LA_MER)
        PurchaseFactory.create(description="tomates", canteen=canteen, category=Purchase.Category.PRODUITS_DE_LA_MER)
        PurchaseFactory.create(description="pommes", canteen=canteen, category=Purchase.Category.FRUITS_ET_LEGUMES)

        response = self.client.get(
            f"{reverse('purchase_list_create')}?category={Purchase.Category.PRODUITS_DE_LA_MER}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 2)

    @authenticate
    def test_filter_by_date(self):
        canteen = CanteenFactory.create()
        canteen.managers.add(authenticate.user)
        PurchaseFactory.create(description="avoine", canteen=canteen, date="2020-01-01")
        PurchaseFactory.create(description="tomates", canteen=canteen, date="2020-01-02")
        PurchaseFactory.create(description="pommes", canteen=canteen, date="2020-02-01")

        response = self.client.get(f"{reverse('purchase_list_create')}?date_after=2020-01-02")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 2)

        response = self.client.get(f"{reverse('purchase_list_create')}?date_before=2020-01-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 1)

        response = self.client.get(f"{reverse('purchase_list_create')}?date_after=2020-01-02&date_before=2020-02-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json().get("results", [])
        self.assertEqual(len(results), 2)

    @authenticate
    def test_available_filter_options(self):
        """
        Test that filter options with data are included in purchases list response
        """
        first_canteen = CanteenFactory.create()
        first_canteen.managers.add(authenticate.user)
        second_canteen = CanteenFactory.create()
        second_canteen.managers.add(authenticate.user)
        PurchaseFactory.create(
            description="avoine",
            canteen=first_canteen,
            category=Purchase.Category.PRODUITS_DE_LA_MER,
            characteristics=[Purchase.Characteristic.BIO],
        )
        PurchaseFactory.create(
            description="tomates",
            canteen=first_canteen,
            category=Purchase.Category.FRUITS_ET_LEGUMES,
            characteristics=[],
        )
        PurchaseFactory.create(
            description="pommes",
            canteen=second_canteen,
            category=Purchase.Category.PRODUITS_LAITIERS,
            characteristics=[],
        )

        not_my_canteen = CanteenFactory.create()
        PurchaseFactory.create(
            description="secret",
            canteen=not_my_canteen,
            category=Purchase.Category.ALIMENTS_INFANTILES,
            characteristics=[Purchase.Characteristic.COMMERCE_EQUITABLE],
        )

        response = self.client.get(f"{reverse('purchase_list_create')}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        categories = body.get("categories", [])
        self.assertEqual(len(categories), 3)
        self.assertIn(Purchase.Category.PRODUITS_DE_LA_MER, categories)
        self.assertNotIn(Purchase.Category.ALIMENTS_INFANTILES, categories)
        self.assertEqual(len(body.get("characteristics", [])), 1)
        canteens = body.get("canteens", [])
        self.assertEqual(len(canteens), 2)
        self.assertNotIn(not_my_canteen.id, canteens)
