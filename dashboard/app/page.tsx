import { redirect } from "next/navigation";

/* The site is a set of static pages under public/c2 — one page per section of
   the walkthrough. The app shell exists only to serve them. */
export default function Home() {
  redirect("/c2/overview.html");
}
