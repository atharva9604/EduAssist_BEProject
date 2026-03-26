import React from 'react';
import { X, Search, BookOpen, ExternalLink, Lightbulb } from 'lucide-react';

interface Paper {
    title: string;
    url: string;
    snippet: string;
}

export interface LookoutData {
    trending_topics: string[];
    recent_papers: Paper[];
}

interface Props {
    show: boolean;
    onClose: () => void;
    data: LookoutData | null;
    loading: boolean;
}

export default function ResearchLookoutModal({ show, onClose, data, loading }: Props) {
    if (!show) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-900 rounded-xl w-full max-w-4xl border border-gray-700 shadow-2xl flex flex-col max-h-[90vh]">
                <div className="flex justify-between items-center p-6 border-b border-gray-800">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-[#DAA520]/20 rounded-lg">
                            <Search className="w-6 h-6 text-[#DAA520]" />
                        </div>
                        <h3 className="text-2xl font-bold text-white">Research Lookout</h3>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto flex-1">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20">
                            <div className="w-12 h-12 border-4 border-gray-700 border-t-[#DAA520] rounded-full animate-spin mb-4"></div>
                            <p className="text-gray-400">Agent is scouring the web for latest research...</p>
                        </div>
                    ) : data ? (
                        <div className="space-y-8">
                            {/* Trending Topics */}
                            <section>
                                <div className="flex items-center gap-2 mb-4">
                                    <Lightbulb className="w-5 h-5 text-yellow-400" />
                                    <h4 className="text-xl font-semibold text-white">Trending Topics</h4>
                                </div>
                                <div className="grid gap-3">
                                    {data.trending_topics?.map((topic, i) => (
                                        <div key={i} className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                                            <p className="text-gray-200">{topic}</p>
                                        </div>
                                    ))}
                                </div>
                            </section>

                            {/* Recent Papers */}
                            <section>
                                <div className="flex items-center gap-2 mb-4">
                                    <BookOpen className="w-5 h-5 text-blue-400" />
                                    <h4 className="text-xl font-semibold text-white">Suggested Readings & Recent Papers</h4>
                                </div>
                                <div className="grid gap-3">
                                    {data.recent_papers?.map((paper, i) => (
                                        <a
                                            key={i}
                                            href={paper.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="block bg-gray-800 p-5 rounded-lg border border-gray-700 hover:border-gray-500 transition group"
                                        >
                                            <div className="flex justify-between items-start gap-4">
                                                <div>
                                                    <h5 className="font-semibold text-blue-400 group-hover:text-blue-300 transition mb-2">
                                                        {paper.title}
                                                    </h5>
                                                    <p className="text-sm text-gray-300">{paper.snippet}</p>
                                                </div>
                                                <ExternalLink className="w-5 h-5 text-gray-500 group-hover:text-blue-400 flex-shrink-0" />
                                            </div>
                                        </a>
                                    ))}
                                </div>
                            </section>
                        </div>
                    ) : (
                        <div className="text-center py-12 text-red-400">
                            Failed to load research data. Please try again.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
