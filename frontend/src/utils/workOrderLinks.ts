export function hasKnownWorkOrderLink(
  links: Record<number, number | null>,
  qaRecordId: number,
): boolean {
  return Object.prototype.hasOwnProperty.call(links, qaRecordId)
}
