"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";

interface DraftSaveButtonProps {
  onSave: () => Promise<void>;
  disabled?: boolean;
}

/** 下書き保存ボタンコンポーネント */
export function DraftSaveButton({ onSave, disabled = false }: DraftSaveButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    setIsLoading(true);
    try {
      await onSave();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => void handleClick()}
      loading={isLoading}
      disabled={disabled || isLoading}
    >
      下書き保存
    </Button>
  );
}
