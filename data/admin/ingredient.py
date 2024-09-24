from django.contrib import admin
from data.models import Ingredient


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    fields = ("name",)
    list_display = ("name",)
