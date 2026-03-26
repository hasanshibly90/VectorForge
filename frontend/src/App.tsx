import { BrowserRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Layout from "./components/Layout";
import UploadPage from "./pages/UploadPage";
import BatchPage from "./pages/BatchPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import PromptsPage from "./pages/PromptsPage";
import SharedViewPage from "./pages/SharedViewPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<UploadPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route path="/batch" element={<BatchPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/login" element={<LoginPage />} />
          </Route>
          <Route path="/s/:token" element={<SharedViewPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
