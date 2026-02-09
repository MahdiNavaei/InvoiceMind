"use client";

import { ReactNode } from "react";

type Tone = "info" | "success" | "warning" | "danger";

type Props = {
  tone?: Tone;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function StatusBlock({ tone = "info", title, description, actions }: Props) {
  return (
    <div className={`status-block ${tone}`}>
      <div className="status-content">
        <p className="status-title">{title}</p>
        <p className="status-description">{description}</p>
      </div>
      {actions ? <div className="status-actions">{actions}</div> : null}
    </div>
  );
}
