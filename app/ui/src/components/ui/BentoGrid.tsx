import React from 'react';

interface BentoGridProps {
    className?: string;
    children?: React.ReactNode;
}

export const BentoGrid = ({ className, children }: BentoGridProps) => {
    return (
        <div
            className={`grid grid-cols-1 md:grid-cols-3 gap-4 max-w-7xl mx-auto ${className}`}
        >
            {children}
        </div>
    );
};

interface BentoGridItemProps {
    className?: string;
    title?: string | React.ReactNode;
    description?: string | React.ReactNode;
    header?: React.ReactNode;
    icon?: React.ReactNode;
}

export const BentoGridItem = ({
    className,
    title,
    description,
    header,
}: BentoGridItemProps) => {
    return (
        <div
            className={`row-span-1 rounded-xl group/bento hover:shadow-xl transition duration-200 p-4 bg-slate-50 border border-slate-100 flex flex-row items-center gap-4 justify-start ${className}`}
        >
            {/* Left: Image */}
            <div className="shrink-0 w-24 h-24 rounded-lg overflow-hidden bg-white shadow-sm border border-slate-100/50">
                {header}
            </div>

            {/* Right: Text */}
            <div className="flex flex-col">
                <div className="font-sans font-bold text-slate-900 mb-1 text-lg">
                    {title}
                </div>
                <div className="font-sans font-normal text-slate-500 text-base leading-relaxed">
                    {description}
                </div>
            </div>
        </div>
    );
};
