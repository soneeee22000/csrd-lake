import Link from "next/link";

export default function NotFound() {
  return (
    <div className="container-page space-y-4 max-w-xl">
      <h1>Not found</h1>
      <p className="text-muted-foreground">
        That page doesn&apos;t exist in CSRD-Lake. The dashboard covers the 10
        CAC 40 companies listed on the home page.
      </p>
      <Link
        href="/"
        className="inline-flex text-primary underline-offset-4 hover:underline"
      >
        Back to the company list
      </Link>
    </div>
  );
}
