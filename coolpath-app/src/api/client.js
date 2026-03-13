import axios from 'axios'

const client = axios.create({
  baseURL: '',           // Vite proxy handles /api and /static → localhost:8000
  timeout: 60000,        // 60s — route computation can be slow on first run
  headers: { 'Content-Type': 'application/json' },
})

export default client
