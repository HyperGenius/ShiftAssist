// frontend/components/holidays/HolidayCalendarForm.stories.tsx
import type { Meta, StoryObj } from "@storybook/react";

import { HolidayLoadingSkeleton } from "./HolidayCalendarForm";

const meta = {
  title: "Holidays/HolidayLoadingSkeleton",
  component: HolidayLoadingSkeleton,
  parameters: {
    layout: "padded",
  },
} satisfies Meta<typeof HolidayLoadingSkeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * 祝日データ取得中に表示されるローディングスケルトン。
 * バックエンドが内閣府Webサイトから祝日を自動投入している間に表示される。
 */
export const Loading: Story = {};
