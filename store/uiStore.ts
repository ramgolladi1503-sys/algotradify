import { create } from "zustand";

type UIStore = {
  selectedOpportunityId: string | null;
  executionPanelOpen: boolean;
  setSelectedOpportunityId: (id: string | null) => void;
  setExecutionPanelOpen: (open: boolean) => void;
};

export const useUIStore = create<UIStore>((set) => ({
  selectedOpportunityId: null,
  executionPanelOpen: false,
  setSelectedOpportunityId: (id) => set({ selectedOpportunityId: id }),
  setExecutionPanelOpen: (open) => set({ executionPanelOpen: open }),
}));
