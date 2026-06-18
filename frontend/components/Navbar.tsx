"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Settings, Database, Sparkles, TrendingUp } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Création", path: "/", icon: Sparkles },
    { name: "Tendances", path: "/trends", icon: TrendingUp },
    { name: "Tableau de bord", path: "/dashboard", icon: Database },
    { name: "Configuration", path: "/settings", icon: Settings },
  ];


  return (
    <nav className="glass-panel sticky top-0 z-50 mb-8 border-b bg-slate-950/80 px-6 py-4">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center space-x-3 transition duration-200 hover:opacity-90">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-rose-500 shadow-md">
            <Compass className="h-6 w-6 text-white animate-spin-slow" />
          </div>
          <div>
            <span className="bg-gradient-to-r from-indigo-200 via-purple-300 to-rose-200 bg-clip-text text-xl font-bold tracking-tight text-transparent">
              Etsy Laser
            </span>
            <span className="ml-1 text-xs font-semibold uppercase tracking-wider text-rose-400">
              Automation
            </span>
          </div>
        </Link>

        {/* Navigation Items */}
        <div className="flex space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`flex items-center space-x-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-indigo-400" : ""}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
