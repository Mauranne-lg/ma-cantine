from rest_framework import serializers

from data.models import Ingredient, Recipe


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        read_only_fields = ("name",)
        fields = ("name",)


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True)

    class Meta:
        model = Recipe
        read_only_fields = ("name", "cooking_time", "instructions", "ingredients", "survey_link")
        fields = ("name", "cooking_time", "instructions", "ingredients", "survey_link")
