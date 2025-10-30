export const runtime = "nodejs";
import { extractPdfText } from "@/lib/pdf";
import { NextRequest, NextResponse } from "next/server";



export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    // The uploaded file should be available as a Blob
    const file: File | null = formData.get("file") as File | null;

    if (!file) {
      return NextResponse.json({ error: "No PDF file uploaded" }, { status: 400 });
    }

    // Get the PDF content as an ArrayBuffer, then convert to Buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);


console.log("DEBUG typeof buffer:", typeof buffer);
console.log("DEBUG isBuffer:", Buffer.isBuffer(buffer));
console.log("DEBUG buffer length:", buffer.length);

    // Confirm type (debug)
    // console.log('Is buffer:', Buffer.isBuffer(buffer), 'Length:', buffer.length)

    const text = await extractPdfText(buffer);
    return NextResponse.json({ text });
  } catch (e: any) {
    console.error("PDF extraction backend error:", e);
    return NextResponse.json({ error: e.message || "Failed" }, { status: 400 });
  }
}