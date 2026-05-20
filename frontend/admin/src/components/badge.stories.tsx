import type { Meta, StoryObj } from "@storybook/react-vite";
import { Badge } from "./badge";
import badgeHistory from "../stories/history/badge.md?raw";

const meta = {
  component: Badge,
  tags: ["ai-generated", "autodocs"],
  args: {
    children: "healthy",
    tone: "success",
    size: "md",
  },
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Badge reutilizável para estados rápidos, níveis de severidade e marcadores compactos em tabelas e cards.\n\n## Histórico de mudanças\n" +
          badgeHistory,
      },
    },
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const States: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Badge tone="neutral">default</Badge>
      <Badge tone="success">loading</Badge>
      <Badge tone="danger">error</Badge>
      <Badge tone="neutral" className="opacity-60">
        disabled
      </Badge>
      <Badge tone="info" className="bg-accent/15">
        hover
      </Badge>
      <Badge tone="warning" className="ring-2 ring-primary ring-offset-2 ring-offset-background">
        focus
      </Badge>
    </div>
  ),
};

export const Variants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <Badge tone="neutral">neutral</Badge>
        <Badge tone="info">info</Badge>
        <Badge tone="success">success</Badge>
        <Badge tone="warning">warning</Badge>
        <Badge tone="danger">danger</Badge>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Badge size="sm">small</Badge>
        <Badge size="md">medium</Badge>
        <Badge size="lg">large</Badge>
      </div>
    </div>
  ),
};

export const Usage: Story = {
  parameters: {
    docs: {
      source: {
        code: `import { Badge } from "@/components/badge";

<Badge tone="warning" size="sm">
  pending approval
</Badge>`,
      },
    },
  },
  render: () => <Badge tone="warning" size="sm">pending approval</Badge>,
};
