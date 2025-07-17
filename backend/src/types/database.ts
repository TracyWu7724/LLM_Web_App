export interface QueryResult {
  columns: string[];
  values: any[][];
}

export interface ApiQueryResponse {
  question: string;
  sql_query: string;
  rows: Record<string, any>[];
  count: number;
  raw_result: string;
}

export interface ApiError {
  detail: string;
} 