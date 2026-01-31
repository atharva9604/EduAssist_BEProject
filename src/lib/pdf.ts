export async function extractPdfText(buffer: Buffer): Promise<string> {
  if (!Buffer.isBuffer(buffer)) {
    throw new Error("extractPdfText expected a Buffer, got " + typeof buffer);
  }

  // ✅ Dynamic import ensures correct module, not pdf-parse's test script
  const { default: pdfParse } = await import("pdf-parse");

  try {
    const data = await pdfParse(buffer);
    return (data.text || "")
      .replace(/\r/g, "")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  } catch (err: any) {
    console.error("Error parsing PDF:", err);
    throw new Error("Failed to parse PDF");
  }
}
