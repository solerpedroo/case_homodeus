/**
 * EN: Home route redirects to /chat (single-page-app style entry).
 * PT: Rota inicial redireciona para /chat (entrada estilo SPA).
 */
import { redirect } from "next/navigation";

export default function Page() {
  redirect("/chat");
}
