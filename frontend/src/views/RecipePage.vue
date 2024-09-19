<template>
  <v-row v-if="!loggedUser" class="d-flex flex-column">
    <p class="text-h6 grey--text text--darken-4 my-8">
      Connectez-vous ou créez un compte pour voir nos recettes
    </p>
  </v-row>
  <v-row v-else-if="!recipes" class="d-flex flex-column">
    <h1 class="text-h2 font-weight-black my-8">
      Oups !
    </h1>
    <p class="text-h6 grey--text text--darken-4 mb-0">
      Nous n'avons pas encore de recette
    </p>
  </v-row>
  <v-row v-else class="mt-4">
    <v-col cols="12" sm="6" md="4" height="100%" class="d-flex flex-column flex-lg-row ga-4">
      <v-card
        class="dsfr d-flex flex-column align-center justify-center ma-2"
        outlined
        min-height="300"
        min-width="300"
        height="80%"
        v-for="recipe in recipes"
        :key="recipe.name"
      >
        <h1 class="font-weight-bold text-center primary--text">{{ recipe.name }}</h1>
        <p>Temps de cuisson : {{ recipe.cookingTime }}</p>
        <ul class="pb-4">
          <p class="my-2 font-weight-bold">Ingrédients</p>
          <li class="pb-4" v-for="ingredient in recipe.ingredients" :key="ingredient.name">{{ ingredient.name }}</li>
        </ul>
        <p class="my-2 font-weight-bold">Instructions</p>
        <p>{{ recipe.instructions }}</p>
      </v-card>
    </v-col>
  </v-row>
</template>

<script>
export default {
  name: "RecipePage",
  data() {
    return {
      loading: false,
      recipes: null,
    }
  },
  computed: {
    loggedUser() {
      return this.$store.state.loggedUser
    },
  },
  methods: {
    setRecipes(recipes) {
      this.recipes = recipes
    },
  },
  beforeMount() {
    this.loading = true
    // TODO : mieux comprendre pq cela permet de gérer le retour de la promesse
    return fetch(`/api/v1/recipes/`)
      .then((response) => {
        if (response.status !== 200 && response.status !== 403) {
          throw new Error()
        }
        response.json().then(this.setRecipes)
      })
      .catch(() => {
        this.$store.dispatch("notify", {
          message: "Désolés, il y a eu une erreur",
          status: "error",
        })
      })
      .finally(() => {
        this.loading = false
      })
  },
}
</script>

<style scoped>
ul {
  padding-left: 0;
  list-style-type: none;
}
</style>
