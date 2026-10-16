"""Tkinter UI for UniScript Ink."""

from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from uniscript_ink.pipeline import render_file


class UniScriptInkApp(tk.Tk):
    """Graphical front-end for UniScript Ink.

    Browse for a .txt/.md file, pick render options, click Render,
    and view the generated handwritten pages.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("UniScript Ink - Handwritten Document Generator")
        self.geometry("620x520")
        self.resizable(False, False)
        self.output_dir: Path | None = None
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        pad = dict(padx=10, pady=5)

        # --- Input file ---
        frm_input = ttk.LabelFrame(self, text="Input Document")
        frm_input.pack(fill="x", **pad)
        self.var_input = tk.StringVar()
        ttk.Entry(frm_input, textvariable=self.var_input, width=52).pack(
            side="left", **pad,
        )
        ttk.Button(frm_input, text="Browse", command=self._browse_input).pack(
            side="left", **pad,
        )

        # --- Render options ---
        frm_opts = ttk.LabelFrame(self, text="Render Options")
        frm_opts.pack(fill="x", **pad)

        row = 0
        ttk.Label(frm_opts, text="Profile:").grid(row=row, column=0, sticky="e", **pad)
        self.var_profile = tk.StringVar(value="everyday")
        ttk.Entry(frm_opts, textvariable=self.var_profile, width=18).grid(
            row=row, column=1, sticky="w", **pad,
        )

        row += 1
        ttk.Label(frm_opts, text="Paper:").grid(row=row, column=0, sticky="e", **pad)
        self.var_paper = tk.StringVar(value="ruled")
        ttk.Entry(frm_opts, textvariable=self.var_paper, width=18).grid(
            row=row, column=1, sticky="w", **pad,
        )

        row += 1
        ttk.Label(frm_opts, text="DPI:").grid(row=row, column=0, sticky="e", **pad)
        self.var_dpi = tk.IntVar(value=200)
        ttk.Spinbox(frm_opts, from_=72, to=600, textvariable=self.var_dpi, width=6).grid(
            row=row, column=1, sticky="w", **pad,
        )

        row += 1
        ttk.Label(frm_opts, text="Format:").grid(row=row, column=0, sticky="e", **pad)
        self.var_format = tk.StringVar(value="pdf")
        ttk.Combobox(
            frm_opts,
            textvariable=self.var_format,
            values=["pdf", "jpg", "png"],
            width=6,
            state="readonly",
        ).grid(row=row, column=1, sticky="w", **pad)

        row += 1
        ttk.Label(frm_opts, text="Reference image:").grid(row=row, column=0, sticky="e", **pad)
        self.var_ref = tk.StringVar()
        ttk.Entry(frm_opts, textvariable=self.var_ref, width=28).grid(
            row=row, column=1, sticky="w", **pad,
        )
        ttk.Button(frm_opts, text="Browse", command=self._browse_ref).grid(
            row=row, column=2, **pad,
        )

        # --- Render button ---
        ttk.Button(self, text="Render", command=self._on_render).pack(pady=8)

        # --- Log ---
        frm_log = ttk.LabelFrame(self, text="Log")
        frm_log.pack(fill="both", expand=True, **pad)
        self.txt_log = tk.Text(frm_log, height=10, state="disabled", wrap="word")
        self.txt_log.pack(fill="both", expand=True, **pad)

        # --- Open folder ---
        self.btn_open = ttk.Button(
            self, text="Open Output Folder", command=self._open_folder, state="disabled",
        )
        self.btn_open.pack(pady=5)

    # --------------------------------------------------------- callbacks
    def _log(self, msg: str) -> None:
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Text / Markdown", "*.txt *.md")],
        )
        if path:
            self.var_input.set(path)

    def _browse_ref(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")],
        )
        if path:
            self.var_ref.set(path)

    def _on_render(self) -> None:
        src = self.var_input.get().strip()
        if not src:
            messagebox.showerror("Error", "Please select an input document.")
            return
        opts = dict(
            out_dir="results/generated_ui",
            profile_name=self.var_profile.get().strip() or "everyday",
            paper_name=self.var_paper.get().strip() or "ruled",
            dpi=self.var_dpi.get(),
            scan_mode="clean",
            image_format=self.var_format.get(),
            quality=92,
            reference_image=self.var_ref.get().strip() or None,
        )
        self._log(f"Rendering {src} ...")
        threading.Thread(target=self._do_render, args=(src, opts), daemon=True).start()

    def _do_render(self, src: str, opts: dict) -> None:
        try:
            result = render_file(src, **opts)
            self.output_dir = Path(opts["out_dir"]).resolve()
            self._log(f"Done - {len(result.output_paths)} page(s):")
            for p in result.output_paths:
                self._log(f"  {p}")
            self._log(f"Manifest: {result.manifest_path}")
            warnings = result.report.get("warnings") or []
            for w in warnings:
                self._log(f"  [{w['code']}] {w['message']}")
            self.btn_open.configure(state="normal")
        except Exception as exc:
            self._log(f"ERROR: {exc}")
            messagebox.showerror("Render error", str(exc))

    def _open_folder(self) -> None:
        if self.output_dir and self.output_dir.is_dir():
            os.startfile(str(self.output_dir))
        else:
            messagebox.showinfo("Info", "Output folder not found.")


def main() -> None:
    app = UniScriptInkApp()
    app.mainloop()


if __name__ == "__main__":
    main()
