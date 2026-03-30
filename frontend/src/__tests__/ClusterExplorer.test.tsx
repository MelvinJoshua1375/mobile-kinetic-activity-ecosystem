import { render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import ClusterExplorer from "../components/ClusterExplorer";
import * as api from "../api";

const MOCK_CLUSTERS = {
  k: 2,
  clusters: [
    {
      cluster_id: 0,
      size: 500000,
      pct: 40.0,
      feature_means: Object.fromEntries(
        ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
         "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z",
         "al_mag","gl_mag","ar_mag","gr_mag"].map((k) => [k, 1.0])
      ),
      top_activities: [{ activity: 0, count: 400000 }],
    },
    {
      cluster_id: 1,
      size: 300000,
      pct: 24.0,
      feature_means: Object.fromEntries(
        ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
         "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z",
         "al_mag","gl_mag","ar_mag","gr_mag"].map((k) => [k, 2.0])
      ),
      top_activities: [{ activity: 1, count: 200000 }],
    },
  ],
};

vi.mock("react-plotly.js", () => ({
  default: () => <div data-testid="plotly-chart" />,
}));

beforeEach(() => {
  vi.spyOn(api.api, "clusters").mockResolvedValue(MOCK_CLUSTERS);
});

test("renders cluster buttons", async () => {
  render(<ClusterExplorer />);
  await waitFor(() => screen.getByText(/Cluster 0/));
  expect(screen.getByText(/Cluster 1/)).toBeInTheDocument();
});

test("shows cluster stats", async () => {
  render(<ClusterExplorer />);
  await waitFor(() => screen.getByText("500,000"));
  expect(screen.getByText("40.00%")).toBeInTheDocument();
});

test("renders plotly chart", async () => {
  render(<ClusterExplorer />);
  await waitFor(() => screen.getByTestId("plotly-chart"));
});
