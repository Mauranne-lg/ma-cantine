import Vue from "vue"
import Vuex from "vuex"
import Constants from "@/constants"
import { diagnosticYears, AuthenticationError } from "../utils"

Vue.use(Vuex)

const headers = {
  "X-CSRFToken": window.CSRF_TOKEN || "",
  "Content-Type": "application/json",
}

const LOCAL_STORAGE_VERSION = "1"
const LOCAL_STORAGE_KEY = `diagnostics-local-${LOCAL_STORAGE_VERSION}`

const verifyResponse = function(response) {
  if (response.status < 200 || response.status >= 400) {
    if (response.status === 403) throw new AuthenticationError()
    else throw new Error(`API responded with status of ${response.status}`)
  }

  const contentType = response.headers.get("content-type")
  const hasJSON = contentType && contentType.startsWith("application/json")

  return hasJSON ? response.json() : response.text()
}

export default new Vuex.Store({
  state: {
    loggedUser: null,

    userLoadingStatus: Constants.LoadingStatus.IDLE,
    blogLoadingStatus: Constants.LoadingStatus.IDLE,
    canteensLoadingStatus: Constants.LoadingStatus.IDLE,
    purchasesLoadingStatus: Constants.LoadingStatus.IDLE,

    sectors: [],
    userCanteenPreviews: [],
    initialDataLoaded: false,

    blogPostCount: null,
    blogPosts: [],
    blogPostsByTag: [],

    notification: {
      message: "",
      status: null,
      title: "",
    },
  },

  mutations: {
    SET_USER_LOADING_STATUS(state, status) {
      state.userLoadingStatus = status
    },
    SET_BLOG_LOADING_STATUS(state, status) {
      state.blogLoadingStatus = status
    },
    SET_CANTEENS_LOADING_STATUS(state, status) {
      state.canteensLoadingStatus = status
    },
    SET_PURCHASES_LOADING_STATUS(state, status) {
      state.purchasesLoadingStatus = status
    },
    SET_LOGGED_USER(state, loggedUser) {
      state.loggedUser = loggedUser
    },
    SET_SECTORS(state, sectors) {
      state.sectors = sectors
    },
    SET_USER_CANTEEN_PREVIEWS(state, userCanteenPreviews) {
      state.userCanteenPreviews = userCanteenPreviews
    },
    ADD_BLOG_POSTS(state, { response, limit, offset, tag }) {
      let paginatedResults = { ...response, limit, offset }
      if (tag) {
        paginatedResults.tag = tag
        state.blogPostsByTag.push(paginatedResults)
      } else {
        state.blogPosts.push(paginatedResults)
        state.blogPostCount = response.count
      }
    },
    SET_INITIAL_DATA_LOADED(state) {
      state.initialDataLoaded = true
    },
    SET_NOTIFICATION(state, { message, title, status }) {
      state.notification.message = message
      state.notification.title = title
      state.notification.status = status
    },
    REMOVE_NOTIFICATION(state, message) {
      if (message && state.notification.message !== message) {
        // in case there was another notification in between, do not remove it
        return
      }
      state.notification.message = null
      state.notification.status = null
      state.notification.title = null
    },
  },

  actions: {
    fetchLoggedUser(context) {
      context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch("/api/v1/loggedUser/")
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_LOGGED_USER", response || null)
          context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch(() => {
          context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.ERROR)
        })
    },

    // It is possible to implement a cache at this level
    fetchCanteen(context, { id }) {
      return fetch(`/api/v1/canteens/${id}`).then((response) => {
        if (response.status != 200) throw new Error()
        return response.json()
      })
    },

    fetchSectors(context) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch("/api/v1/sectors/")
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_SECTORS", response)
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch(() => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
        })
    },

    fetchUserCanteenPreviews(context) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch("/api/v1/canteenPreviews/")
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_USER_CANTEEN_PREVIEWS", response)
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch(() => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
        })
    },

    fetchBlogPosts(context, { limit = 6, offset, tag }) {
      context.commit("SET_BLOG_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      let url = `/api/v1/blogPosts/?limit=${limit}&offset=${offset}`
      if (tag) url += `&tag=${tag}`
      return fetch(url)
        .then(verifyResponse)
        .then((response) => {
          context.commit("ADD_BLOG_POSTS", { response, limit, offset, tag })
          context.commit("SET_BLOG_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch(() => {
          context.commit("SET_BLOG_LOADING_STATUS", Constants.LoadingStatus.ERROR)
        })
    },

    fetchInitialData(context) {
      return Promise.all([context.dispatch("fetchLoggedUser"), context.dispatch("fetchSectors")])
        .then(() => {
          if (context.state.loggedUser) return context.dispatch("fetchUserCanteenPreviews")
        })
        .then(() => {
          const criticalLoadingStatuses = ["canteensLoadingStatus"]
          const hasError = criticalLoadingStatuses.some((x) => context.state[x] === Constants.LoadingStatus.ERROR)
          if (hasError) throw new Error("Une erreur s'est produite lors du chargement des données intiales")
          else context.commit("SET_INITIAL_DATA_LOADED")
        })
    },

    updateProfile(context, { payload }) {
      context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/user/${context.state.loggedUser.id}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_LOGGED_USER", response)
          context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch((e) => {
          context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    changePassword(context, { payload }) {
      context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch("/api/v1/passwordChange/", { method: "PUT", headers, body: JSON.stringify(payload) })
        .then((response) => {
          if (response.status === 400) {
            return response.json().then((jsonResponse) => {
              throw new Error(Object.values(jsonResponse).join(", "))
            })
          }
          return verifyResponse(response)
        })
        .then(() => {
          context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch((e) => {
          context.commit("SET_USER_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    createCanteen(context, { payload }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/`, { method: "POST", headers, body: JSON.stringify(payload) })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    updateCanteen(context, { id, payload }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/${id}`, { method: "PATCH", headers, body: JSON.stringify(payload) })
        .then(verifyResponse)
        .then(() => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    publishCanteen(context, { id, payload }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/${id}/publish`, { method: "POST", headers, body: JSON.stringify(payload) })
        .then(verifyResponse)
        .then(() => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    unpublishCanteen(context, { id, payload }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/${id}/unpublish`, { method: "POST", headers, body: JSON.stringify(payload) })
        .then(verifyResponse)
        .then(() => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    deleteCanteen(context, { id }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/${id}`, { method: "DELETE", headers })
        .then(verifyResponse)
        .then(() => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    createDiagnostic(context, { canteenId, payload }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/${canteenId}/diagnostics/`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    updateDiagnostic(context, { canteenId, id, payload }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/canteens/${canteenId}/diagnostics/${id}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    saveLocalStorageDiagnostic(context, diagnostic) {
      let savedDiagnostics = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || "{}")
      savedDiagnostics[diagnostic.year] = diagnostic
      return localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(savedDiagnostics))
    },

    removeLocalStorageDiagnostics() {
      return localStorage.removeItem(LOCAL_STORAGE_KEY)
    },

    subscribeBetaTester(context, payload) {
      return fetch("/api/v1/subscribeBetaTester/", { method: "POST", headers, body: JSON.stringify(payload) }).then(
        verifyResponse
      )
    },

    subscribeNewsletter(context, email) {
      return fetch("/api/v1/subscribeNewsletter/", { method: "POST", headers, body: JSON.stringify({ email }) }).then(
        verifyResponse
      )
    },

    addManager(context, { canteenId, email }) {
      return fetch(`/api/v1/addManager/`, {
        method: "POST",
        headers,
        body: JSON.stringify({ canteenId, email }),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    sendCanteenEmail(context, payload) {
      return fetch("/api/v1/contactCanteen/", { method: "POST", headers, body: JSON.stringify(payload) }).then(
        verifyResponse
      )
    },

    sendCanteenNotFoundEmail(context, payload) {
      return fetch("/api/v1/canteenNotFoundMessage/", { method: "POST", headers, body: JSON.stringify(payload) }).then(
        verifyResponse
      )
    },

    removeManager(context, { canteenId, email }) {
      return fetch(`/api/v1/removeManager/`, {
        method: "POST",
        headers,
        body: JSON.stringify({ canteenId, email }),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    importDiagnostics(context, payload) {
      let form = new FormData()
      form.append("file", payload.file)
      return fetch(`/api/v1/importDiagnostics/`, {
        method: "POST",
        headers: {
          "X-CSRFToken": window.CSRF_TOKEN || "",
        },
        body: form,
      }).then(verifyResponse)
    },

    notify(context, { title, message, status }) {
      context.commit("SET_NOTIFICATION", { title, message, status })
      setTimeout(() => context.commit("REMOVE_NOTIFICATION", message), 4000)
    },
    notifyRequiredFieldsError(context) {
      const title = null
      const message = "Merci de vérifier les champs en rouge et réessayer"
      const status = "error"
      context.dispatch("notify", { title, message, status })
    },
    notifyServerError(context, error) {
      const title = "Oops !"
      const message =
        error instanceof AuthenticationError
          ? "Votre session a expiré. Rechargez la page et reconnectez-vous pour continuer."
          : "Une erreur est survenue, vous pouvez réessayer plus tard ou nous contacter directement à contact@egalim.beta.gouv.fr"
      const status = "error"
      context.dispatch("notify", { title, message, status })
    },
    removeNotification(context) {
      context.commit("REMOVE_NOTIFICATION")
    },

    submitTeledeclaration(context, { id }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      const payload = {
        diagnosticId: id,
      }
      return fetch("/api/v1/createTeledeclaration/", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((diagnostic) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return diagnostic
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    cancelTeledeclaration(context, { id }) {
      context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      const payload = {
        teledeclarationId: id,
      }
      return fetch("/api/v1/cancelTeledeclaration/", {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((diagnostic) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return diagnostic
        })
        .catch((e) => {
          context.commit("SET_CANTEENS_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    sendInquiryEmail(_, payload) {
      return fetch("/api/v1/inquiry/", { method: "POST", headers, body: JSON.stringify(payload) }).then(verifyResponse)
    },

    createPurchase(context, { payload }) {
      context.commit("SET_PURCHASES_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/purchases/`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_PURCHASES_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_PURCHASES_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },

    updatePurchase(context, { id, payload }) {
      context.commit("SET_PURCHASES_LOADING_STATUS", Constants.LoadingStatus.LOADING)
      return fetch(`/api/v1/purchases/${id}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(payload),
      })
        .then(verifyResponse)
        .then((response) => {
          context.commit("SET_PURCHASES_LOADING_STATUS", Constants.LoadingStatus.SUCCESS)
          return response
        })
        .catch((e) => {
          context.commit("SET_PURCHASES_LOADING_STATUS", Constants.LoadingStatus.ERROR)
          throw e
        })
    },
  },

  getters: {
    getLocalDiagnostics: () => () => {
      const savedDiagnostics = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (!savedDiagnostics) {
        return diagnosticYears().map((year) => Object.assign({}, Constants.DefaultDiagnostics, { year }))
      }
      return Object.values(JSON.parse(savedDiagnostics))
    },
    getCanteenUrlComponent: () => (canteen) => {
      return `${canteen.id}--${canteen.name}`
    },
  },
})
