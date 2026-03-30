import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import LivePredictor from "../components/LivePredictor";
import * as api from "../api";

const MOCK_RESULT = {
  cluster: 0,
  anomaly_score: 0.12,
  is_anomaly: false,
  distances_to_centroids: { "0": 0.5, "1": 2.3 },
  magnitudes: { al_mag: 9.81, gl_mag: 0.01, ar_mag: 0.01, gr_mag: 9.8 },
};

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="plotly-chart" />,
}));

beforeEach(() => {
  vi.spyOn(api.api, "predict").mockResolvedValue(MOCK_RESULT);
});

test("renders form inputs", () => {
  render(<LivePredictor />);
  expect(screen.getByText("Live Predictor")).toBeInTheDocument();
  expect(screen.getByText("Predict Cluster")).toBeInTheDocument();
});

test("submits and shows result", async () => {
  render(<LivePredictor />);
  fireEvent.click(screen.getByText("Predict Cluster"));
  await waitFor(() => screen.getByText("Cluster 0"));
  expect(screen.getByText("0.1200")).toBeInTheDocument();
  expect(screen.getByText("NO")).toBeInTheDocument();
});

test("shows error on API failure", async () => {
  vi.spyOn(api.api, "predict").mockRejectedValue(new Error("Network error"));
  render(<LivePredictor />);
  fireEvent.click(screen.getByText("Predict Cluster"));
  await waitFor(() => screen.getByText(/Network error/));
});
