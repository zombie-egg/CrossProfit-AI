"use client";

import { useEffect } from "react";
import { useAuth } from "@/components/auth-provider";
import translations from "@/lib/auto-translations.json";

const dictionary = translations as Record<string, string>;
const textState = new WeakMap<Text, { original: string; rendered: string }>();
const attrState = new WeakMap<Element, Map<string, { original: string; rendered: string }>>();

function translate(value: string, locale: "zh" | "en"): string {
  if (locale === "zh") return value;
  const trimmed = value.trim();
  const replacement = dictionary[trimmed];
  if (!replacement) return value;
  return value.replace(trimmed, replacement);
}

function translateTree(root: Node, locale: "zh" | "en") {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node: Node | null;
  while ((node = walker.nextNode())) {
    const text = node as Text;
    const parent = text.parentElement;
    if (!parent || parent.closest("script, style, textarea, [data-no-translate]")) continue;
    const prior = textState.get(text);
    const original = prior && text.nodeValue === prior.rendered ? prior.original : text.nodeValue ?? "";
    const rendered = translate(original, locale);
    textState.set(text, { original, rendered });
    if (text.nodeValue !== rendered) text.nodeValue = rendered;
  }
  if (!(root instanceof Element)) return;
  for (const element of [root, ...root.querySelectorAll("[placeholder], [title], [aria-label]")]) {
    const values = attrState.get(element) ?? new Map();
    for (const name of ["placeholder", "title", "aria-label"]) {
      const value = element.getAttribute(name);
      if (value === null) continue;
      const prior = values.get(name);
      const original = prior && value === prior.rendered ? prior.original : value;
      const rendered = translate(original, locale);
      values.set(name, { original, rendered });
      if (value !== rendered) element.setAttribute(name, rendered);
    }
    attrState.set(element, values);
  }
}

export function LocaleDom() {
  const { locale } = useAuth();
  useEffect(() => {
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
    let scheduled = false;
    const sync = () => { if (scheduled) return; scheduled = true; requestAnimationFrame(() => { scheduled = false; translateTree(document.body, locale); }); };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "title", "aria-label"] });
    return () => observer.disconnect();
  }, [locale]);
  return null;
}
