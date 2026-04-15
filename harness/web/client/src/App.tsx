import { useWebSocket } from "./hooks/useWebSocket";
import { Layout } from "./components/Layout";

export default function App() {
  useWebSocket();
  return <Layout />;
}
