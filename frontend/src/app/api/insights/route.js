import { supabase } from '../../../lib/supabase';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * GET /api/insights
 *
 * Returns cached global insights from the insights_cache table.
 * The backend pipeline recomputes these once per cycle.
 */
export async function GET() {
  try {
    const { data, error } = await supabase
      .from('insights_cache')
      .select('insights, computed_at')
      .eq('id', 1)
      .single();

    if (error) {
      console.error('insights_cache query error:', error);
      return NextResponse.json({ insights: [], computed_at: null }, { status: 200 });
    }

    let insights = data?.insights || [];
    if (typeof insights === 'string') {
      try { insights = JSON.parse(insights); }
      catch { insights = []; }
    }

    return NextResponse.json({
      insights,
      computed_at: data?.computed_at || null,
    });
  } catch (err) {
    console.error('GET /api/insights error:', err);
    return NextResponse.json({ insights: [], computed_at: null }, { status: 500 });
  }
}
