// frontend/.storybook/preview.ts
import type { Preview } from "@storybook/react";
import "../app/globals.css";

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: "dark",
      values: [
        { name: "dark", value: "#020617" }, // slate-950
      ],
    },
  },
};

export default preview;
