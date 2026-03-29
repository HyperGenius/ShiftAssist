import Link from "next/link";

export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center p-8">
      <div className="text-center max-w-md">
        <h1 className="text-4xl font-bold tracking-widest text-cyan-300 mb-4">
          SHIFT<span className="text-slate-400">ASSIST</span>
        </h1>
        <p className="text-slate-400 mb-8">シフト管理システム</p>
        <Link
          href="/workers"
          className="inline-block px-6 py-3 bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 rounded font-medium tracking-wider uppercase hover:bg-cyan-500/30 transition-all"
        >
          対応者管理へ →
        </Link>
      </div>
    </main>
  );
}
