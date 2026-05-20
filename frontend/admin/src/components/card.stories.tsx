import type { Meta, StoryObj } from "@storybook/react-vite";
import { ArrowUpRight } from "lucide-react";
import { Card } from "./card";
import { Badge } from "./badge";
import cardHistory from "../stories/history/card.md?raw";

const meta = {
  component: Card,
  tags: ["ai-generated", "autodocs"],
  args: {
    eyebrow: "Reliability",
    title: "Readiness score",
    description: "Use cards para organizar métricas, alerts e recomendações do painel.",
    variant: "default",
    padding: "md",
  },
  parameters: {
    docs: {
      description: {
        component:
          "Container reutilizável para compor blocos de informação do frontend, com variantes de elevação, criticidade e interação.\n\n## Histórico de mudanças\n" +
          cardHistory,
      },
    },
  },
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {
  render: (args) => (
    <Card {...args} action={<Badge tone="success">healthy</Badge>}>
      <p className="text-3xl font-black tracking-tight text-foreground">98.4%</p>
    </Card>
  ),
};

export const States: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="grid w-[860px] gap-4 md:grid-cols-2 xl:grid-cols-3">
      <Card title="Default" description="Estado base." />
      <Card variant="interactive" title="Hover" description="Visual de hover permanente para revisão." className="translate-y-[-2px] shadow-xl shadow-primary/10" />
      <Card variant="elevated" title="Loading" description="Indique carregamento via conteúdo placeholder.">
        <div className="space-y-2">
          <div className="h-3 w-2/3 rounded bg-secondary" />
          <div className="h-8 w-1/2 rounded bg-secondary" />
        </div>
      </Card>
      <Card variant="critical" title="Error" description="Card para incidentes ou bloqueios." />
      <Card title="Disabled" description="Representado por opacidade reduzida." className="opacity-60" />
      <Card
        title="Focus"
        description="Estados de foco podem ser aplicados ao bloco clicável."
        className="ring-2 ring-primary ring-offset-2 ring-offset-background"
      />
    </div>
  ),
};

export const Variants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="grid w-[860px] gap-4 md:grid-cols-2">
      <Card variant="default" title="Default" description="Resumo operacional." />
      <Card variant="elevated" title="Elevated" description="Destaque para KPIs." />
      <Card variant="interactive" title="Interactive" description="Usado em links de navegação." action={<ArrowUpRight className="h-4 w-4" />} />
      <Card variant="critical" title="Critical" description="Contexto de alerta ou compliance." />
    </div>
  ),
};

export const Usage: Story = {
  parameters: {
    docs: {
      source: {
        code: `import { Badge } from "@/components/badge";
import { Card } from "@/components/card";

<Card
  eyebrow="Performance"
  title="P95 de inferência"
  description="Latência agregada dos últimos 15 minutos."
  action={<Badge tone="warning">attention</Badge>}
>
  <p className="text-3xl font-black">842 ms</p>
</Card>`,
      },
    },
  },
  render: () => (
    <Card
      eyebrow="Performance"
      title="P95 de inferência"
      description="Latência agregada dos últimos 15 minutos."
      action={<Badge tone="warning">attention</Badge>}
    >
      <p className="text-3xl font-black">842 ms</p>
    </Card>
  ),
};
