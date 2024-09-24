from rest_framework.generics import ListAPIView

from api.permissions import IsAuthenticated
from api.serializers import RecipeSerializer
from data.models import Recipe


class RecipeListView(ListAPIView):
    model = Recipe
    serializer_class = RecipeSerializer
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthenticated]
