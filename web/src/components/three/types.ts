export interface GraphNode3D {
  id: string;
  kind: 'user' | 'job' | 'skill' | 'occupation';
  label: string;
  degree: number;
  occupation?: string;
  skills?: string[];
  x: number;
  y: number;
  z: number;
}

export interface GraphEdge3D {
  source: string;
  target: string;
  edge_type: string;
  is_public: boolean;
}

export interface FederatedHero3DProps {
  className?: string;
  nClients?: number;
  recallScore?: number;
}

export interface JobGraphExplorer3DProps {
  nodes: GraphNode3D[];
  edges: GraphEdge3D[];
  mode: '3d' | '2d';
  showPublic: boolean;
  showPrivate: boolean;
  highlightIds?: string[];
  selectedNodeId?: string | null;
  onSelectNode?: (node: GraphNode3D | null) => void;
  className?: string;
}
