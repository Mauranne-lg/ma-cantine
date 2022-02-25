from datetime import date
from django.db import models
from data.fields import ChoiceArrayField
from .canteen import Canteen


class Purchase(models.Model):
    class Meta:
        verbose_name = "achat"
        verbose_name_plural = "achats"
        ordering = ["-date", "-creation_date"]

    class Category(models.TextChoices):
        VIANDES_VOLAILLES = "VIANDES_VOLAILLES", "Viandes, volailles"
        PRODUITS_DE_LA_MER = "PRODUITS_DE_LA_MER", "Produits de la mer"
        FRUITS_ET_LEGUMES = "FRUITS_ET_LEGUMES", "Fruits, légumes, légumineuses et oléagineux"
        PRODUITS_CEREALIERS = "PRODUITS_CEREALIERS", "Produits céréaliers"
        ENTREES = "ENTREES", "Entrées et plats composés"
        PRODUITS_LAITIERS = "PRODUITS_LAITIERS", "Lait et produits laitiers"
        BOISSONS = "BOISSONS", "Boissons"
        AIDES = "AIDES", "Aides culinaires et ingrédients divers"
        BEURRE_OEUF_FROMAGE = "BEURRE_OEUF_FROMAGE", "Beurre, oeuf, fromage"
        PRODUITS_SUCRES = "PRODUITS_SUCRES", "Produits sucrés"
        ALIMENTS_INFANTILES = "ALIMENTS_INFANTILES", "Aliments infantiles"
        GLACES_SORBETS = "GLACES_SORBETS", "Glaces et sorbets"
        AUTRES = "AUTRES", "Autres"

    class Characteristic(models.TextChoices):
        BIO = "BIO", "Bio"
        CONVERSION_BIO = "CONVERSION_BIO", "En conversion bio"
        LABEL_ROUGE = "LABEL_ROUGE", "Label rouge"
        AOCAOP = "AOCAOP", "AOC / AOP"
        # ICP here is a typo
        IGP = "ICP", "Indication géographique protégée"
        STG = "STG", "Spécialité traditionnelle garantie"
        HVE = "HVE", "Haute valeur environnementale"
        PECHE_DURABLE = "PECHE_DURABLE", "Pêche durable"
        RUP = "RUP", "Région ultrapériphérique"
        FERMIER = "FERMIER", "Fermier"
        EXTERNALITES = (
            "EXTERNALITES",
            "Produit prenant en compte les coûts imputés aux externalités environnementales pendant son cycle de vie",
        )
        COMMERCE_EQUITABLE = "COMMERCE_EQUITABLE", "Commerce équitable"
        PERFORMANCE = "PERFORMANCE", "Produits acquis sur la base de leurs performances en matière environnementale"
        EQUIVALENTS = "EQUIVALENTS", "Produits équivalents"

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)

    canteen = models.ForeignKey(Canteen, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    description = models.TextField(null=True, blank=True, verbose_name="Description du produit")
    provider = models.TextField(null=True, blank=True, verbose_name="Fournisseur")
    category = models.CharField(
        max_length=255, choices=Category.choices, null=True, blank=True, verbose_name="Catégorie"
    )
    characteristics = ChoiceArrayField(
        base_field=models.CharField(
            max_length=255, choices=Characteristic.choices, null=True, blank=True, verbose_name="Caractéristique"
        ),
        blank=True,
        null=True,
        size=None,
        verbose_name="Caractéristiques",
    )
    price_ht = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="Prix HT",
    )
    invoice_file = models.FileField(null=True, blank=True, upload_to="invoices/%Y/")

    @property
    def readable_category(self):
        if not self.category:
            return None
        try:
            return Purchase.Category(self.category).label
        except Exception:
            return None

    @property
    def readable_characteristics(self):
        if not self.characteristics:
            return None
        valid_characteristics = []
        for characteristic in self.characteristics:
            try:
                valid_characteristics.append(Purchase.Characteristic(characteristic).label)
            except Exception:
                pass
        return ", ".join(valid_characteristics) if valid_characteristics else None
