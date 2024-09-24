from django import forms
from django.contrib import admin
from data.models import Recipe


class RecipeForm(forms.ModelForm):
    class Meta:
        widgets = {
            "name": forms.Textarea(attrs={"cols": 35, "rows": 1}),
            "cooking_time": forms.TimeInput(attrs={"type": "time"}),
            "instructions": forms.Textarea(attrs={"cols": 55, "rows": 2}),
        }


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeForm
    fields = ("name", "cooking_time", "instructions", "ingredients", "survey_link")
    list_display = ("name", "cooking_time", "instructions", "survey_link")
