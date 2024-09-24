from ckeditor.fields import RichTextField
from django.db import models


class Ingredient(models.Model):
    class Meta:
        verbose_name = "ingrédient"
        verbose_name_plural = "ingrédients"

    name = models.CharField(max_length=100, verbose_name="nom")

    def __str__(self) -> str:
        return self.name


class Recipe(models.Model):
    class Meta:
        verbose_name = "recette"
        verbose_name_plural = "recettes"

    name = models.CharField(max_length=100, verbose_name="titre")
    instructions = RichTextField(
        verbose_name="Instructions",
        default="<ul><li>Etape 1 : </li><li>Etape 2 : </li></ul><p>Bon appétit !</p>",
    )
    cooking_time = models.DurationField(verbose_name="temps de cuisson")
    ingredients = models.ManyToManyField(Ingredient, verbose_name="ingrédients")
    survey_link = models.URLField(null=True, blank=True)
