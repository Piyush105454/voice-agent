"use client";
// next/dynamic does not forward refs, so the graph instance is passed through an explicit prop.
import ForceGraph2D from "react-force-graph-2d";

export default function ForceGraph({ fgRef, ...props }: { fgRef: React.MutableRefObject<any> } & Record<string, any>) {
  return <ForceGraph2D ref={fgRef} {...(props as any)} />;
}
