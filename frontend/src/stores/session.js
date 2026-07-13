import { defineStore } from "pinia";
import { ref } from "vue";
import { apiEnvelope } from "../api";
export const useSession = defineStore("session", () => {
    const username = ref(localStorage.getItem("kylin-user") || "");
    const mode = ref(localStorage.getItem("kylin-mode") || "READ_ONLY");
    async function login(user, password) {
        const result = await apiEnvelope("/auth/login", { method: "POST", body: JSON.stringify({ username: user, password }) });
        localStorage.setItem("kylin-token", result.data.access_token);
        localStorage.setItem("kylin-user", user);
        localStorage.setItem("kylin-mode", result.meta.mode);
        username.value = user;
        mode.value = result.meta.mode;
    }
    function logout() { localStorage.clear(); username.value = ""; }
    return { username, mode, login, logout };
});
