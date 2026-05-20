import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "./button";
import { Toast, showToast } from "./toast";
import toastHistory from "../stories/history/toast.md?raw";

const meta = {
  component: Toast,
  tags: ["ai-generated", "autodocs"],
  args: {
    title: "Deploy concluído",
    description: "A release 1.9.8 foi promovida para produção sem erros.",
    tone: "success",
  },
  parameters: {
    docs: {
      description: {
        component:
          "Toast reutilizável para feedback operacional, com helper imperativo para acionar notificações Sonner no app.\n\n## Histórico de mudanças\n" +
          toastHistory,
      },
    },
  },
} satisfies Meta<typeof Toast>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const States: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="grid w-[840px] gap-4 md:grid-cols-2">
      <Toast title="Default" description="Feedback simples." />
      <Toast title="Hover" description="Ação com destaque para revisão." tone="info" actionLabel="Abrir" />
      <Toast title="Loading" description="Processo ainda em andamento." tone="success" isLoading />
      <Toast title="Disabled" description="Ação desabilitada visualmente." tone="neutral" actionLabel="Fechado" />
      <Toast title="Error" description="Falha ao validar as credenciais do cluster." tone="danger" />
      <Toast title="Focus" description="Estado de foco representado na ação primária." tone="warning" actionLabel="Revisar" />
    </div>
  ),
};

export const Variants: Story = {
  parameters: {
    controls: { disable: true },
  },
  render: () => (
    <div className="grid w-[840px] gap-4 md:grid-cols-2">
      <Toast title="Neutral" tone="neutral" />
      <Toast title="Info" tone="info" />
      <Toast title="Success" tone="success" />
      <Toast title="Warning" tone="warning" />
      <Toast title="Danger" tone="danger" />
    </div>
  ),
};

export const Usage: Story = {
  parameters: {
    docs: {
      source: {
        code: `import { Button } from "@/components/button";
import { showToast } from "@/components/toast";

<Button
  onClick={() =>
    showToast({
      tone: "success",
      title: "Rollback finalizado",
      description: "A release anterior foi restaurada com sucesso.",
      actionLabel: "Ver incidente",
    })
  }
>
  Disparar toast
</Button>`,
      },
    },
  },
  render: () => (
    <Button
      onClick={() =>
        showToast({
          tone: "success",
          title: "Rollback finalizado",
          description: "A release anterior foi restaurada com sucesso.",
          actionLabel: "Ver incidente",
        })
      }
    >
      Disparar toast
    </Button>
  ),
};
