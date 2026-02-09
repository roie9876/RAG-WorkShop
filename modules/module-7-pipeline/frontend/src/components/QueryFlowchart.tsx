import { useMemo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { QueryDecomposition, MultiHopStep } from '../types'

interface QueryFlowchartProps {
  decomposition?: QueryDecomposition
  multiHopTrace?: MultiHopStep[]
}

export function QueryFlowchart({ decomposition, multiHopTrace }: QueryFlowchartProps) {
  const { nodes, edges } = useMemo(() => {
    const nodes: Node[] = []
    const edges: Edge[] = []

    if (!decomposition && !multiHopTrace) {
      return { nodes, edges }
    }

    // Original query node
    const originalQuery = decomposition?.original_query || 'Query'
    nodes.push({
      id: 'original',
      position: { x: 250, y: 0 },
      data: {
        label: (
          <div className="text-center">
            <div className="font-medium text-xs">Original Query</div>
            <div className="text-xs text-muted-foreground max-w-32 truncate">
              {originalQuery}
            </div>
          </div>
        ),
      },
      style: {
        background: 'hsl(var(--primary))',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        padding: '8px 12px',
      },
    })

    // Sub-query nodes
    if (decomposition?.sub_queries) {
      const subQueryCount = decomposition.sub_queries.length
      const spacing = 150
      const startX = 250 - ((subQueryCount - 1) * spacing) / 2

      decomposition.sub_queries.forEach((sq, idx) => {
        const nodeId = `subquery-${idx}`
        nodes.push({
          id: nodeId,
          position: { x: startX + idx * spacing, y: 100 },
          data: {
            label: (
              <div className="text-center">
                <div className="text-xs max-w-28 truncate">{sq.query}</div>
                <div className="text-xs text-green-600">{sq.results_count} hits</div>
              </div>
            ),
          },
          style: {
            background: 'hsl(var(--muted))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            padding: '8px',
          },
        })

        edges.push({
          id: `edge-original-${nodeId}`,
          source: 'original',
          target: nodeId,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: 'hsl(var(--muted-foreground))' },
        })
      })
    }

    // Multi-hop trace nodes
    if (multiHopTrace && multiHopTrace.length > 0) {
      let yOffset = decomposition?.sub_queries ? 200 : 100

      multiHopTrace.forEach((step, idx) => {
        const nodeId = `hop-${idx}`
        
        // Skip if this is a duplicate of a sub-query
        if (decomposition?.sub_queries?.some(sq => sq.query === step.query)) {
          return
        }

        nodes.push({
          id: nodeId,
          position: { x: 250, y: yOffset },
          data: {
            label: (
              <div className="text-center">
                <div className="font-medium text-xs">Iteration {step.iteration}</div>
                <div className="text-xs max-w-32 truncate">{step.query}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {step.reasoning}
                </div>
              </div>
            ),
          },
          style: {
            background: 'hsl(var(--accent))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '8px',
            padding: '8px',
          },
        })

        // Connect to previous node
        const sourceId = idx === 0 
          ? (decomposition?.sub_queries ? `subquery-${Math.floor(decomposition.sub_queries.length / 2)}` : 'original')
          : `hop-${idx - 1}`

        edges.push({
          id: `edge-hop-${idx}`,
          source: sourceId,
          target: nodeId,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: 'hsl(var(--muted-foreground))' },
          animated: true,
        })

        yOffset += 80
      })
    }

    // Final answer node
    const finalY = nodes.length > 1 ? Math.max(...nodes.map(n => n.position.y)) + 80 : 100
    nodes.push({
      id: 'answer',
      position: { x: 250, y: finalY },
      data: {
        label: (
          <div className="text-center">
            <div className="font-medium text-xs">Final Answer</div>
            <div className="text-xs">with citations</div>
          </div>
        ),
      },
      style: {
        background: 'hsl(142 76% 36%)',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        padding: '8px 12px',
      },
    })

    // Connect last node to answer
    const lastNodeId = nodes.length > 2 
      ? nodes[nodes.length - 2].id 
      : 'original'
    
    edges.push({
      id: 'edge-to-answer',
      source: lastNodeId,
      target: 'answer',
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: 'hsl(var(--muted-foreground))' },
    })

    return { nodes, edges }
  }, [decomposition, multiHopTrace])

  if (nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
        No query decomposition data available
      </div>
    )
  }

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
      attributionPosition="bottom-left"
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <Controls />
    </ReactFlow>
  )
}
