import { defineStore } from "pinia";
import { ref } from "vue";
import { apiEnvelope } from "../api";

export const useSession = defineStore("session", () => {
  const username = ref(localStorage.getItem("kylin-user") || "");
  const mode = ref(localStorage.getItem("kylin-mode") || "CONTROLLED_EXECUTION");
  async function login(user: string, password: string) {
    const result = await apiEnvelope<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username: user, password }) });
    localStorage.setItem("kylin-token", result.data.access_token); localStorage.setItem("kylin-user", user); localStorage.setItem("kylin-mode", result.meta.mode); username.value = user; mode.value = result.meta.mode;
  }
  function logout() {
    localStorage.removeItem("kylin-token");
    localStorage.removeItem("kylin-user");
    localStorage.removeItem("kylin-mode");
    username.value = "";
    mode.value = "CONTROLLED_EXECUTION";
  }
  return { username, mode, login, logout };
});
