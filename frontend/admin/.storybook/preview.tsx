import type { Preview } from "@storybook/react-vite";
import "../src/index.css";
import { ThemeProvider } from "../src/components/theme-provider";
import { ToasterHost } from "../src/components/toast";

const preview: Preview = {
  decorators: [
    (Story) => (
      <ThemeProvider defaultTheme="light" storageKey="storybook-theme">
        <div className="min-h-screen bg-background p-6 text-foreground">
          <Story />
          <ToasterHost />
        </div>
      </ThemeProvider>
    ),
  ],
  parameters: {
    actions: {
      argTypesRegex: "^on[A-Z].*",
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
      expanded: true,
      disableSaveFromUI: true,
    },
    viewport: {
      options: {
        desktopWide: {
          name: "Desktop 1440",
          styles: {
            width: "1440px",
            height: "1024px",
          },
          type: "desktop",
        },
        laptop: {
          name: "Laptop 1280",
          styles: {
            width: "1280px",
            height: "800px",
          },
          type: "desktop",
        },
        tablet: {
          name: "Tablet 768",
          styles: {
            width: "768px",
            height: "1024px",
          },
          type: "tablet",
        },
        mobile: {
          name: "Mobile 390",
          styles: {
            width: "390px",
            height: "844px",
          },
          type: "mobile",
        },
      },
      defaultViewport: "desktopWide",
    },
    a11y: {
      test: "todo",
    },
    layout: "padded",
  },
};

export default preview;
