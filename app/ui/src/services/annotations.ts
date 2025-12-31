import { AnnotationFactory } from 'annotpdf'
import { HighlightAnnotationObj } from 'annotpdf/lib/annotations/text_markup_annotation'

let annotator: AnnotationFactory

/**
 * Initialises an annotator with the PDF file
 * @param pdfBytes PDF file as a Uint8Array
 */
export function initAnnotations(pdfBytes: Uint8Array): Uint8Array {
  annotator = new AnnotationFactory(pdfBytes)
  annotator.write()
  // Add a dummy annotation to initialise the annotation layer
  const [pdfBytesWithAnnots] = addAnnotation(1, [0, 0, 0, 0, 0, 0, 0, 0])
  return pdfBytesWithAnnots
}

/**
 * Adds a highlight annotation to the PDF
 * @param page_num Page number
 * @param quad Quad coordinates - distance from bottom left of document in the format:
 * [x1, y1, (top left corner) x2, y2 (top right), x3, y3 (bottom left), x4, y4 (bottom right)]
 */
export function addAnnotation(
  page_num: number,
  quad: number[],
  color = { r: 255, g: 255, b: 0 }
): [Uint8Array, HighlightAnnotationObj] {
  const page = page_num - 1 // Annotation library page numbering starts from 0
  const annotation = annotator.createHighlightAnnotation({
    page,
    color,
    quadPoints: quad,
    opacity: 0.5
  })
  return [annotator.write(), annotation]
}

/**
 * Deletes an annotation from the PDF
 * @param id Annotation ID
 */
export function deleteAnnotation(id: string): Uint8Array {
  annotator.deleteAnnotation(id)
  return annotator.write()
}
