<script setup>
import { RouterView, useRoute } from "vue-router"
import { reactive, computed, watch } from "vue"
import AppHeader from "@/components/AppHeader.vue"
import AppFooter from "@/components/AppFooter.vue"
import BreadcrumbsNav from "@/components/BreadcrumbsNav.vue"
import NotificationCenter from "@/components/NotificationCenter.vue"

const layout = reactive({ fullscreen: false })
const routerViewClass = computed(() => (layout.fullscreen ? "" : "fr-container fr-pb-2w"))

const route = useRoute()
watch(route, (to) => {
  const suffix = "ma cantine"
  document.title = to.meta.title ? to.meta.title + " - " + suffix : suffix

  layout.fullscreen = to.meta.fullscreen
})
</script>

<template>
  <div>
    <AppHeader v-if="!layout.fullscreen" />

    <main :class="routerViewClass">
      <BreadcrumbsNav v-if="!layout.fullscreen" />
      <RouterView />
    </main>

    <AppFooter v-if="!layout.fullscreen" />

    <NotificationCenter />
  </div>
</template>

<style>
#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
fieldset {
  border: none;
}
.justify-space-between {
  justify-content: space-between;
}
</style>
