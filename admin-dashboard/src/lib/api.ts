import axios from "axios";

// Create an Axios instance pointing to the FastAPI backend
export const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    headers: {
        "Content-Type": "application/json",
    },
});

// Generic SWR fetcher utilizing our Axios instance
export const fetcher = (url: string) => apiClient.get(url).then((res) => res.data);

// Action specific functions
export const runPipeline = async (userId: string) => {
    const response = await apiClient.post(`/admin/users/${userId}/run_pipeline`);
    return response.data;
};
