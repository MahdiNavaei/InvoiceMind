"use client";

import { ReactNode } from "react";

type Props = {
  title: string;
  description: string;
  actions?: ReactNode;
};

export function EmptyBlock({ title, description, actions }: Props) {
  return (
    <div className="empty-block">
      <p className="empty-title">{title}</p>
      <p className="empty-description">{description}</p>
      {actions ? <div className="inline-actions">{actions}</div> : null}
    </div>
  );
}
