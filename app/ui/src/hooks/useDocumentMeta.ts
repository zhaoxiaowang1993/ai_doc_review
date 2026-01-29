import { useEffect } from 'react';

interface DocumentMeta {
    title?: string;
    description?: string;
    canonical?: string;
    ogTitle?: string;
    ogDescription?: string;
}

/**
 * 自定义 hook 用于动态设置页面 meta 标签
 * 轻量级替代 react-helmet-async
 */
export function useDocumentMeta(meta: DocumentMeta) {
    useEffect(() => {
        // 保存原始值用于清理
        const originalTitle = document.title;

        // 设置 title
        if (meta.title) {
            document.title = meta.title;
        }

        // 设置 description
        if (meta.description) {
            let descMeta = document.querySelector('meta[name="description"]') as HTMLMetaElement | null;
            const originalDesc = descMeta?.content;
            if (!descMeta) {
                descMeta = document.createElement('meta');
                descMeta.name = 'description';
                document.head.appendChild(descMeta);
            }
            descMeta.content = meta.description;

            // 清理时恢复
            return () => {
                document.title = originalTitle;
                if (originalDesc !== undefined && descMeta) {
                    descMeta.content = originalDesc;
                }
            };
        }

        // 设置 canonical
        if (meta.canonical) {
            let canonicalLink = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
            const originalCanonical = canonicalLink?.href;
            if (!canonicalLink) {
                canonicalLink = document.createElement('link');
                canonicalLink.rel = 'canonical';
                document.head.appendChild(canonicalLink);
            }
            canonicalLink.href = meta.canonical;

            return () => {
                document.title = originalTitle;
                if (originalCanonical !== undefined && canonicalLink) {
                    canonicalLink.href = originalCanonical;
                }
            };
        }

        return () => {
            document.title = originalTitle;
        };
    }, [meta.title, meta.description, meta.canonical]);
}
