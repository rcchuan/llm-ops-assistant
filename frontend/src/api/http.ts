import axios from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL

if (!baseURL) {
  throw new Error("缺少 VITE_API_BASE_URL 配置")
}

export const http = axios.create({
  baseURL,
  timeout: 5000,
})
