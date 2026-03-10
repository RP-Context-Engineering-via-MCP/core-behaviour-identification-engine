import axios from "axios";

// Create an Axios instance pointing to the FastAPI backend
export const apiClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:6009",
    headers: {
        "Content-Type": "application/json",
    },
});

export const processorClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_PROCESSOR_URL || "http://localhost:6010",
    headers: {
        "Content-Type": "application/json",
    },
});

// Generic SWR fetcher utilizing our Axios instance for lightweight API
export const fetcher = (url: string) => apiClient.get(url).then((res) => res.data);

// Generic SWR fetcher utilizing our Axios instance for heavy Processor API
export const processorFetcher = (url: string) => processorClient.get(url).then((res) => res.data);

// Action specific functions
export const runPipeline = async (userId: string, forceFullRun: boolean = false) => {
    const response = await processorClient.post(
        `/admin/users/${userId}/run_pipeline?force_full_run=${forceFullRun}`
    );
    return response.data;
};
