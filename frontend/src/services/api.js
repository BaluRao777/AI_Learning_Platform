import axios from "axios";

const API = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:5000",
  timeout: 15000
});

// 🔐 Attach token automatically
API.interceptors.request.use(
  (req) => {
    const token = localStorage.getItem("token");

    if (token) {
      req.headers.Authorization = `Bearer ${token}`;
    }

    return req;
  },
  (error) => Promise.reject(error)
);

API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

// 🚀 API FUNCTIONS

export const generateContent = async (data) => {
  // Local AI (Qwen analysis + Gemini) can take longer than the default timeout.
  const res = await API.post("/generate", data, { timeout: 120000 });
  return res;
};

export const getHistory = async () => {
  const res = await API.get("/history");
  return res;
};

export const loginUser = async (data) => {
  const res = await API.post("/login", data);
  return res;
};

export const signupUser = async (data) => {
  const res = await API.post("/signup", data);
  return res;
};

export default API;