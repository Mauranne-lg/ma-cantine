import pandas as pd
import datetime
import math
import logging
import requests
import json
import os
import time

from abc import ABC, abstractmethod
from data.department_choices import Department
from data.region_choices import Region
from data.models import Canteen, Teledeclaration, Sector
from api.serializers import SectorSerializer
from api.views.utils import camelize
from django.core.files.storage import default_storage
from django.db.models import Q
from django.core.cache import cache

logger = logging.getLogger(__name__)


CAMPAIGN_DATES = {
    2021: {"start_date": datetime.date(2022, 7, 16), "end_date": datetime.date(2022, 12, 5)},
    2022: {"start_date": datetime.date(2023, 2, 13), "end_date": datetime.date(2023, 6, 30)},
}


def map_epcis_communes():
    """
    Create a dict that maps cities with their EPCI code
    """
    epcis = {}
    try:
        logger.info("Starting communes dl")
        response = requests.get("https://geo.api.gouv.fr/communes", timeout=50)
        response.raise_for_status()
        communes = response.json()
        for commune in communes:
            try:
                epcis[commune['code']] = commune['codeEpci']  # Caching the data
            except KeyError:  # This commune doesn't have an EPCI code
                pass
    except requests.exceptions.HTTPError as e:
        logger.info(e)
        return None
    return epcis


def fetch_epci(code_insee_commune, epcis):
    """
    Provide EPCI code for a city, given the insee code of the city
    """
    if code_insee_commune and code_insee_commune in epcis.keys():
        return epcis[code_insee_commune]
    else:
        return None


def fetch_sector(sector_id):
    """
    Provide the sector informations, given the sector id
    Queries each sector only once, storing the data in cache after
    """
    if (sector_id and not math.isnan(sector_id)):
        cached_data = cache.get(sector_id)
        if cached_data:
            return cached_data
        else:
            sector = camelize(SectorSerializer(Sector.objects.get(id=sector_id)).data)
            cache.set(sector_id, sector, timeout=3600)  # Timeout in seconds
            return sector
    else:
        return ""


def map_canteens_td(year):
    """
    Populate cache for a given year. The cache indicates if one canteen ahs participated in campaign
    """
    # Check and fetch Teledeclaration data from the database
    tds = Teledeclaration.objects.filter(
            year=year,
            creation_date__range=(
                CAMPAIGN_DATES[year]["start_date"],
                CAMPAIGN_DATES[year]["end_date"],
            ),
            status=Teledeclaration.TeledeclarationStatus.SUBMITTED,
        ).values("canteen_id", "declared_data")

    # Populate TD_CACHE for the given year
    cache_ = []
    for td in tds:
        cache_.append(td['canteen_id']) 
        if 'satellites' in td['declared_data']:
            for satellite in td['declared_data']['satellites']:
                cache_.append(satellite['id'])
    return cache_


class ETL(ABC):
    def __init__(self):
        self.df = None
        self.schema = None
        self.schema_url = ""
        self.dataset_name = ""

    def _fill_geo_name(self, geo_zoom="department"):
        """
        Given a dataframe with a column 'department' or 'region', this method maps the name of the location, based on the INSEE code
        Returns:
            pd.Series: The names of the location corresponding to an INSEE code, for each line of the dataset
        """
        if "department" in geo_zoom:
            geo = {i.value: i.label for i in Department}
        elif "region" in geo_zoom:
            geo = {i.value: i.label for i in Region}
        else:
            logger.warning(
                "The desired geo zoom for the method _fill_geo_zoom() is not possible. Please choose between 'department' and 'region'"
            )
            return 0

        self.df[f"{geo_zoom}_lib"] = self.df[geo_zoom].apply(
            lambda x: geo[x].split(" - ")[1].lstrip() if isinstance(x, str) else None
        )

    def transform_geo_data(self, geo_col_names=["department", "region"]):
        for geo in geo_col_names:
            logger.info("Start filling geo_name")
            self._fill_geo_name(geo_zoom=geo)
            col_geo = self.df.pop(f"{geo}_lib")
            self.df.insert(self.df.columns.get_loc(geo) + 1, f"{geo}_lib", col_geo)
        if 'city_insee_code' in self.df.columns:
            epcis = map_epcis_communes()
            self.df['epci'] = self.df['city_insee_code'].apply(lambda x: fetch_epci(x, epcis))
        else:
            self.df['epci'] = None

    def _clean_dataset(self):
        columns = [i["name"].replace("canteen_", "canteen.") for i in self.schema["fields"]]

        self.df = self.df.loc[:, ~self.df.columns.duplicated()]

        self.df = self.df.reindex(columns, axis="columns")
        self.df.columns = self.df.columns.str.replace(".", "_")
        self.df = self.df.drop_duplicates(subset=["id"])
        self.df = self.df.reset_index(drop=True)

        for col_int in self.schema["fields"]:
            if col_int["type"] == "integer":
                # Force column o Int64 to maintain an integer column despite the NaN values
                self.df[col_int["name"]] = self.df[col_int["name"]].astype("Int64")
            if col_int["type"] == "float":
                self.df[col_int["name"]] = self.df[col_int["name"]].round(decimals=4)
        self.df = self.df.replace("<NA>", "")

    def _extract_sectors(self):
        # Fetching sectors information and aggreting in list in order to have only one row per canteen
        self.df["sectors"] = self.df["sectors"].apply(fetch_sector)
        canteens_sectors = self.df.groupby("id")["sectors"].apply(list).apply(lambda x: x if x != [""] else [])
        del self.df["sectors"]

        return self.df.merge(canteens_sectors, on="id")

    @abstractmethod
    def extract_dataset(self):
        pass

    def get_schema(self):
        return self.schema

    def get_dataset(self):
        return self.df

    def len_dataset(self):
        if isinstance(self.df, pd.DataFrame):
            return len(self.df)
        else:
            return 0

    def is_valid(self) -> bool:
        dataset_to_validate_url = f"{os.environ['CELLAR_HOST']}/{os.environ['CELLAR_BUCKET_NAME']}/media/open_data/{self.dataset_name}_to_validate.csv"
        schema_url = "https://github.com/betagouv/ma-cantine/blob/staging/data/schemas/schema_teledeclaration.json"

        res = requests.get(
            f"https://api.validata.etalab.studio/validate?schema={schema_url}&url={dataset_to_validate_url}&header_case=true"
        )
        report = json.loads(res.text)["report"]
        if len(report["errors"]) > 0:
            logger.error(f"The dataset {self.dataset_name} extraction has errors : ")
            logger.error(report["errors"])
            return 0
        else:
            return 1

    def export_dataset(self, stage="to_validate"):
        if stage == "to_validate":
            filename = f"open_data/{self.dataset_name}_to_validate.csv"
        elif stage == 'validated':
            filename = f"open_data/{self.dataset_name}.csv"
        else:
            return 0
        with default_storage.open(filename, "w") as file:
            self.df.to_csv(file, sep=";", index=False, na_rep="")


class ETL_CANTEEN(ETL):
    def __init__(self):
        super().__init__()
        self.dataset_name = "registre_cantines"
        self.schema = json.load(open("data/schemas/schema_cantine.json"))
        self.schema_url = (
            "https://raw.githubusercontent.com/betagouv/ma-cantine/staging/data/schemas/schema_cantine.json"
        )

    def extract_dataset(self):
        all_canteens_col = [i["name"] for i in self.schema["fields"]]
        canteens_col_from_db = all_canteens_col.copy()
        for col_processed in ['active_on_ma_cantine', 'department_lib', 'region_lib', 'epci', 'declaration_donnees_2021']:
            canteens_col_from_db.remove(col_processed)

        exclude_filter = Q(sectors__id=22)  # Filtering out the police / army sectors
        exclude_filter |= Q(deletion_date__isnull=False)  # Filtering out the deleted canteens
        start = time.time()
        canteens = Canteen.objects.exclude(exclude_filter)
        end = time.time()
        logger.info(f'Time spent on canteens extraction : {end - start}')
        if canteens.count() == 0:
            return pd.DataFrame(columns=canteens_col_from_db)

        # Creating a dataframe with all canteens. The canteens can have multiple lines if they have multiple sectors
        self.df = pd.DataFrame(canteens.values(*canteens_col_from_db))

        # Adding the active_on_ma_cantine column
        start = time.time()
        non_active_canteens = Canteen.objects.filter(managers=None).values_list("id", flat=True)
        end = time.time()
        logger.info(f'Time spent on active canteens : {end - start}')
        self.df["active_on_ma_cantine"] = self.df["id"].apply(lambda x: x not in non_active_canteens)

        logger.info("Canteens : Extract sectors...")
        self.df = self._extract_sectors()

        bucket_url = os.environ.get("CELLAR_HOST")
        bucket_name = os.environ.get("CELLAR_BUCKET_NAME")
        self.df["logo"] = self.df["logo"].apply(lambda x: f"{bucket_url}/{bucket_name}/media/{x}" if x else "")

        logger.info("Canteens : Clean dataset...")
        self._clean_dataset()

        logger.info("Canteens : Fill geo name...")
        start = time.time()
        self.transform_geo_data(geo_col_names=["department", "region"])
        end = time.time()
        logger.info(f'Time spent on geo data : {end - start}')

        logger.info("Canteens : Fill campaign participations...")
        start = time.time()
        for year in [2021]:
            campaign_participation = map_canteens_td(year)
            self.df['declaration_donnees_2021'] = self.df['id'].apply(lambda x: x in campaign_participation)
        end = time.time()
        logger.info(f'Time spent on campaign participations : {end - start}')


class ETL_TD(ETL):
    def __init__(self, year: int):
        super().__init__()
        self.year = year
        self.dataset_name = f"campagne_td_{year}"
        self.schema = json.load(open("data/schemas/schema_teledeclaration.json"))
        self.schema_url = (
            "https://raw.githubusercontent.com/betagouv/ma-cantine/staging/data/schemas/schema_teledeclaration.json"
        )
        self.categories_to_aggregate = {
            "bio": ["_bio"],
            "sustainable": ["_sustainable", "_label_rouge", "_aocaop_igp_stg"],
            "egalim_others": ["_egalim_others", "_hve", "_peche_durable", "_rup", "_fermier", "_commerce_equitable"],
            "externality_performance": ["_externality_performance", "_performance", "_externalites"],
        }

    def extract_dataset(self):
        if self.year in CAMPAIGN_DATES.keys():
            self.df = pd.DataFrame(
                Teledeclaration.objects.filter(
                    year=self.year,
                    creation_date__range=(
                        CAMPAIGN_DATES[self.year]["start_date"],
                        CAMPAIGN_DATES[self.year]["end_date"],
                    ),
                    status=Teledeclaration.TeledeclarationStatus.SUBMITTED,
                    canteen_id__isnull=False,
                ).values()
            )
        else:
            logger.warning(f"TD campagne dataset does not exist for year : {self.year}")
            return pd.DataFrame()
    
        if len(self.df) == 0:
            logger.warning(f"TD campagne dataset is empty for year : {self.year}")
            return pd.DataFrame()

        logger.info("TD campagne : Flatten declared data...")
        self.df = self._flatten_declared_data()

        logger.info("TD campagne : Aggregate appro data for complete TD...")
        self._aggregate_complete_td()

        self.df["teledeclaration_ratio_bio"] = (
            self.df["teledeclaration.value_bio_ht"] / self.df["teledeclaration.value_total_ht"]
        )
        self.df["teledeclaration_ratio_egalim_hors_bio"] = (
            self.df["teledeclaration.value_sustainable_ht"] / self.df["teledeclaration.value_total_ht"]
        )
        self.df["teledeclaration_type"] = self.df["teledeclaration.diagnostic_type"]  # Renaming to match schema

        logger.info("TD campagne : Clean dataset...")
        self._clean_dataset()
        logger.info("TD campagne : Filter by sector...")
        self._filter_by_sectors()
        logger.info("TD Campagne : Fill geo name...")
        self.transform_geo_data(geo_col_names=["canteen_department", "canteen_region"])

    def _flatten_declared_data(self):
        tmp_df = pd.json_normalize(self.df["declared_data"])
        self.df = pd.concat([self.df.drop("declared_data", axis=1), tmp_df], axis=1)
        return self.df

    def _aggregation_col(self, categ="bio", sub_categ=["_bio"]):
        pattern = "|".join(sub_categ)
        self.df[f"teledeclaration.value_{categ}_ht"] = self.df.filter(regex=pattern).sum(
            axis=1, numeric_only=True, skipna=True, min_count=1
        )

    def _aggregate_complete_td(self):
        """
        Aggregate the columns of a complete TD for an appro category if the total value of this category is not specified.
        """
        for categ, elements_in_categ in self.categories_to_aggregate.items():
            self._aggregation_col(categ, elements_in_categ)

    def _filter_by_sectors(self):
        """
        Filtering the sectors of the police and army so they do not appear publicly
        """
        canteens_to_filter = Canteen.objects.filter(sectors__name='Restaurants des armées / police / gendarmerie')
        canteens_id_to_filter = [canteen.id for canteen in canteens_to_filter]
        self.df = self.df[~self.df["canteen_id"].isin(canteens_id_to_filter)]
