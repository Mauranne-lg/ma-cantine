
from rest_framework.generics import ListAPIView
from data.models import Recipe
from api.serializers import RecipeSerializer
from api.permissions import (
    IsAuthenticated
)
class RecipeListView(ListAPIView):
    model = Recipe
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticated]
