// Email · Figma node 2:2 · Screens / Sign up
// Figma design-to-code reference (2026-10-30). Not production code: adapt it to your components.
// Tokens appear as var(--<figma variable>, <fallback>): load tokens/tokens.css.

export default function EmailStep() {
  return (
    <div className="flex h-[844px] w-[390px] flex-col bg-white px-7 pb-10 pt-11">
      <h1 className="text-[28px] font-bold leading-tight text-[#1b1f2a]">Email</h1>
      <p className="mt-2 text-[15px] text-[#667085]">We'll send your plant reminders there.</p>
      <button className="mt-auto rounded-[14px] bg-[var(--brand,#5a78dc)] py-4 font-semibold text-white">
        Continue
      </button>
    </div>
  );
}
