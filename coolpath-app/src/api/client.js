import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || ''

const client = axios.create({
  baseURL: baseURL,
  timeout: 60000,        // 60s — route computation can be slow on first run
  headers: { 'Content-Type': 'application/json' },
})

export default client

