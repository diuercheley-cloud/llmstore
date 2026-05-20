import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect } from "storybook/test";
import { Loader2 } from "lucide-react";
import { Button } from "./button";
import buttonHistory from "../stories/history/button.md?raw";

const meta = {
  component: Button,
  tags: ["ai-generated", "autodocs"],
  args: {
    children: "Executar ação",
    variant: "primary",
    size: "md",
    disabled: false,
    isLoading: false,
  },
  argTypes: {
    onClick: { action: "clicked" },
  },
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Botão base do frontend administrativo. Usa variantes visuais consistentes com o tema global e expõe props tipadas para loading, tamanho e semântica de ação.\n\n## Histórico de mudanças\n" +
          buttonHistory,
      },
    },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {
  play: async ({ canvas }) => {
    await expect(canvas.getByRole("button", { name: /executar ação/i })).toBeVisible();
  },
};

export const States: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="grid w-[720px] gap-4 md:grid-cols-2">
      <Button>Default</Button>
      <Button className="bg-primary/90 shadow-2xl shadow-primary/30">Hover</Button>
      <Button isLoading>Loading</Button>
      <Button disabled>Disabled</Button>
      <Button variant="destructive">Error</Button>
      <Button className="ring-2 ring-primary ring-offset-2 ring-offset-background">Focus</Button>
    </div>
  ),
};

export const Variants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="flex w-[760px] flex-wrap gap-3">
      <Button variant="primary">Primary</Button>
      <Button variant="secondary">Secondary</Button>
      <Button variant="outline">Outline</Button>
      <Button variant="ghost">Ghost</Button>
      <Button variant="accent">Accent</Button>
      <Button variant="destructive">Danger</Button>
      <Button size="sm">Small</Button>
      <Button size="lg">Large</Button>
      <Button size="icon" aria-label="Refreshing">
        <Loader2 className="h-4 w-4" />
      </Button>
    </div>
  ),
};

export const Usage: Story = {
  parameters: {
    docs: {
      source: {
        code: `import { Button } from "@/components/button";

<Button
  variant="accent"
  size="lg"
  isLoading={isDeploying}
  onClick={handleDeploy}
>
  Publicar Storybook
</Button>`,
      },
    },
  },
  render: () => <Button variant="accent" size="lg">Publicar Storybook</Button>,
};

export const CssCheck: Story = {
  args: {
    children: "Submit",
  },
  play: async ({ canvas }) => {
    const button = canvas.getByRole("button", { name: /submit/i });
    await expect(getComputedStyle(button).backgroundColor).toBe("rgb(13, 148, 136)");
  },
};
