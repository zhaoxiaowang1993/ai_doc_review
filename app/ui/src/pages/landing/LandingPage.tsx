import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    CheckmarkCircleRegular,
    PersonRegular,
    BuildingRegular,
} from '@fluentui/react-icons';
import './landing.css';

// Assets
import heroBg from '../../assets/landing/hero_bg.png';
import featureAi from '../../assets/landing/feature_ai.png';
import featureRules from '../../assets/landing/feature_rules.png';
import featureSecurity from '../../assets/landing/feature_security.png';
import logoNew from '../../assets/landing/logo_new.png';

export default function LandingPage() {
    const navigate = useNavigate();

    // Typewriter effect
    const [typewriterText, setTypewriterText] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);
    const [loopNum, setLoopNum] = useState(0);
    const [typingSpeed, setTypingSpeed] = useState(150);

    const docTypes = ["医疗文书", "法律合同", "自媒体文案", "商务标书", "财务发票"];

    useEffect(() => {
        const handleType = () => {
            const i = loopNum % docTypes.length;
            const fullText = docTypes[i];

            setTypewriterText(isDeleting
                ? fullText.substring(0, typewriterText.length - 1)
                : fullText.substring(0, typewriterText.length + 1)
            );

            setTypingSpeed(isDeleting ? 80 : 150);

            if (!isDeleting && typewriterText === fullText) {
                setTimeout(() => setIsDeleting(true), 1500); // Pause at end
            } else if (isDeleting && typewriterText === '') {
                setIsDeleting(false);
                setLoopNum(loopNum + 1);
            }
        };

        const timer = setTimeout(handleType, typingSpeed);
        return () => clearTimeout(timer);
    }, [typewriterText, isDeleting, loopNum, typingSpeed]);

    const testimonials = [
        {
            quote: "以前手动查敏感词要半小时，现在一键搞定，再也没被限流！",
            author: "自媒体博主 @小红书达人",
            icon: <PersonRegular />
        },
        {
            quote: "AI 帮我揪出很多合同漏洞，客户都说我专业度高了。",
            author: "某律所合伙人 王律师",
            icon: <PersonRegular />
        },
        {
            quote: "文书合规率从75%升到98%，医保罚款直接清零。",
            author: "某三甲医院 质控科李主任",
            icon: <BuildingRegular />
        },
        {
            quote: "标书审核快了60%，废标率降80%，中标金额翻一番。",
            author: "建筑公司 投标负责人张总",
            icon: <BuildingRegular />
        },
        {
            quote: "财务报销审核效率提升了3倍，再也不用加班对票据了。",
            author: "科技公司 财务经理刘姐",
            icon: <PersonRegular />
        },
        {
            quote: "对于我们这种跨国业务，多语言合同审核简直是救星。",
            author: "外贸企业 法务总监Michael",
            icon: <BuildingRegular />
        },
        {
            quote: "原来总是担心广告法违规，现在发布前扫一下，安心多了。",
            author: "电商运营 负责人赵赵",
            icon: <PersonRegular />
        },
        {
            quote: "招标文件里的坑都被识别出来了，避免了巨大的经济损失。",
            author: "工程咨询公司 高级顾问",
            icon: <BuildingRegular />
        }
    ];

    const featureItems = useMemo(() => ([
        {
            title: "通用基础能力",
            subtitle: "从源头把控质量，夯实文档规范基础",
            image: featureAi,
            bullets: [
                { strong: "敏感词检测", text: "语义级识别，不漏检" },
                { strong: "语义语法/错别字检查", text: "纠正语句不通、文字错误" },
                { strong: "文件格式检查", text: "统一字体、页码、行距等规范" },
            ],
        },
        {
            title: "垂直行业能力",
            subtitle: "专懂你的行话，精准匹配业务场景",
            image: featureRules,
            bullets: [
                { strong: "合同审核", text: "条款合规、风险点提示" },
                { strong: "医疗文书审核", text: "医保合规、病历完整性校验" },
                { strong: "招投标文件审核", text: "资质匹配、格式合规检查" },
                { strong: "财务票据审核", text: "发票真伪、报销规则匹配" },
            ],
        },
        {
            title: "企业级进阶能力",
            subtitle: "为组织赋能，构建全流程风控闭环",
            image: featureSecurity,
            bullets: [
                { strong: "数据库联动", text: "对接企业内部系统，批量审核文件" },
                { strong: "自动审核闭环", text: "审核→预警→整改→复核全流程" },
                { strong: "多角色权限", text: "管理员/审核员/普通用户权限分离" },
                { strong: "审核报告导出", text: "支持数据可视化，方便复盘" },
            ],
        },
    ]), []);

    const [activeFeatureIndex, setActiveFeatureIndex] = useState(0);
    const featureSentinelsRef = useRef<Array<HTMLDivElement | null>>([]);

    useEffect(() => {
        const raf = window.requestAnimationFrame(() => {
            const sentinels = featureSentinelsRef.current.filter(Boolean) as HTMLDivElement[];
            if (sentinels.length === 0) return;

            const observer = new IntersectionObserver(
                (entries) => {
                    const visible = entries.filter((e) => e.isIntersecting);
                    if (visible.length === 0) return;

                    visible.sort((a, b) => (b.intersectionRatio || 0) - (a.intersectionRatio || 0));
                    const target = visible[0]?.target as HTMLDivElement | undefined;
                    const idxRaw = target?.dataset.index;
                    const idx = idxRaw != null ? Number(idxRaw) : 0;
                    if (!Number.isNaN(idx)) setActiveFeatureIndex(idx);
                },
                {
                    root: null,
                    rootMargin: "-30% 0px -55% 0px",
                    threshold: [0.01, 0.25, 0.5, 0.75],
                }
            );

            sentinels.forEach((node) => observer.observe(node));
        });

        return () => window.cancelAnimationFrame(raf);
    }, []);

    const handleTryIt = () => {
        navigate('/files');
    };

    return (
        <div className="lp-container dark-theme">
            {/* Background Ambience */}
            <div className="lp-bg-ambience">
                <div className="lp-star-field"></div>
                <div className="lp-nebula"></div>
            </div>

            {/* Header */}
            <header className="lp-header">
                <div className="lp-wrapper lp-header-content">
                    <div className="lp-logo">
                        <img src={logoNew} alt="Logo" className="lp-logo-img" style={{ height: '32px' }} />
                        <span>文件审核专家</span>
                    </div>
                    <nav className="lp-nav">
                        {/* Future Nav Links */}
                    </nav>
                    <div className="lp-header-actions">
                        <button className="lp-btn lp-btn-primary" onClick={handleTryIt}>
                            免费使用
                        </button>
                    </div>
                </div>
            </header>

            {/* Hero Section */}
            <section className="lp-hero" style={{ backgroundImage: `url(${heroBg})` }}>
                <div className="lp-overlay"></div>
                <div className="lp-wrapper lp-hero-content">
                    <div className="lp-hero-text">
                        <h1 className="lp-hero-title">
                            <span className="lp-typewriter-text">{typewriterText}</span>
                            <span className="lp-cursor">|</span>，AI 智能审核
                        </h1>
                        <p className="lp-hero-desc">
                            内置多行业规则，支持自定义审核标准。让每一份文档都无懈可击。
                        </p>
                        <div className="lp-hero-actions centered">
                            <button className="lp-btn lp-btn-primary lp-btn-lg lp-glow-effect" onClick={handleTryIt}>
                                免费使用
                            </button>
                        </div>
                        <div className="lp-trust-badges">
                            <span><CheckmarkCircleRegular /> 内置 20+ 行业规则</span>
                            <span><CheckmarkCircleRegular /> 搭载最强基座大模型</span>
                            <span><CheckmarkCircleRegular /> 自主学习审核规则</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Pain Points Section */}
            <section className="lp-section lp-pain-points">
                <div className="lp-wrapper">
                    <h2 className="lp-section-title">这些文件审核痛点，AI 帮你一键解决</h2>
                    <div className="lp-pain-grid">
                        <PainCard
                            role="自媒体创作者"
                            pain="文案踩敏感词，发布就限流下架"
                            solve="AI 精准检测敏感词，自定义平台规则，发布前快速校验"
                            spriteClass="lp-sprite-media"
                        />
                        <PainCard
                            role="法务/律师"
                            pain="合同条款疏漏，暗藏法律风险"
                            solve="内置法规规则，自动识别漏洞歧义，降低纠纷概率"
                            spriteClass="lp-sprite-legal"
                        />
                        <PainCard
                            role="医院质控人员"
                            pain="医疗文书不合规，被医保局扣分罚款"
                            solve="匹配医保审核标准，校验文书规范，避免质控不合格"
                            spriteClass="lp-sprite-medical"
                        />
                        <PainCard
                            role="投标人员"
                            pain="标书不合规，直接废标错失商机"
                            solve="对标招投标要求，检查格式条款，提高中标率"
                            spriteClass="lp-sprite-bidding"
                        />
                        <PainCard
                            role="财务人员"
                            pain="发票/报销单数据出错，核账返工"
                            solve="校验票据信息真实性，匹配报销规则，减少财务风险"
                            spriteClass="lp-sprite-finance"
                        />
                    </div>
                </div>
            </section>

            {/* Core Advantages */}
            <section className="lp-section lp-advantages">
                <div className="lp-wrapper">
                    <h2 className="lp-section-title">为什么选我们的 AI 审核智能体？</h2>
                    <div className="lp-adv-grid">
                        <div className="lp-adv-card">
                            <div className="lp-adv-img">
                                <img src={featureRules} alt="Rules" />
                            </div>
                            <h3>内置多行业规则，开箱即用</h3>
                            <p>覆盖法律、医疗、招投标等高频行业，规则实时更新。不用自己搭规则，一键切换审核标准，省80%时间。</p>
                        </div>
                        <div className="lp-adv-card">
                            {/* Unified Image Style */}
                            <div className="lp-adv-img">
                                <img src={featureRules} alt="Custom Rules" style={{ filter: 'hue-rotate(90deg)' }} />
                            </div>
                            <h3>零门槛自定义规则，多形式导入</h3>
                            <p>支持文字描述、文档/表格上传，自动生成审核规则。非技术人员也能操作，适配自媒体、医疗等专属需求。</p>
                        </div>
                        <div className="lp-adv-card">
                            <div className="lp-adv-img">
                                <img src={featureAi} alt="AI Learning" />
                            </div>
                            <h3>AI 自学习，规则库越用越精准</h3>
                            <p>人工标注「采纳/不采纳/编辑」审核建议，AI 自动解析并升级规则库。审核标准越用越贴合业务，无需手动维护规则。</p>
                        </div>
                    </div>
                </div>
            </section>

            <section className="lp-section lp-scroll-features">
                <div className="lp-wrapper">
                    <h2 className="lp-section-title">三大核心能力，覆盖全场景</h2>
                    <div className="lp-scrollmagic">
                        {/* Sentinel 区域 - 用于触发滚动切换 */}
                        <div className="lp-scrollmagic-track">
                            {featureItems.map((_, idx) => (
                                <div
                                    key={idx}
                                    className="lp-scrollmagic-sentinel"
                                    data-index={idx}
                                    ref={(el) => {
                                        featureSentinelsRef.current[idx] = el;
                                    }}
                                />
                            ))}
                        </div>
                        {/* 固定显示的内容面板 */}
                        <div className="lp-scrollmagic-sticky">
                            <div key={activeFeatureIndex} className="lp-scrollmagic-content fade-in">
                                <div className="lp-scrollmagic-text">
                                    <div className="lp-feature-indicator">
                                        {featureItems.map((_, idx) => (
                                            <span
                                                key={idx}
                                                className={`lp-indicator-dot ${idx === activeFeatureIndex ? 'active' : ''}`}
                                            />
                                        ))}
                                    </div>
                                    <h3 className="lp-feature-title">{featureItems[activeFeatureIndex]?.title}</h3>
                                    <p className="lp-feature-subtitle">{featureItems[activeFeatureIndex]?.subtitle}</p>
                                    <ul className="lp-feature-list-new">
                                        {featureItems[activeFeatureIndex]?.bullets.map((b, idx) => (
                                            <li key={idx}>
                                                <CheckmarkCircleRegular />
                                                <span>
                                                    <strong>{b.strong}</strong>：{b.text}
                                                </span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="lp-scrollmagic-visual">
                                    <img
                                        src={featureItems[activeFeatureIndex]?.image}
                                        alt={featureItems[activeFeatureIndex]?.title}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Testimonials */}
            <section className="lp-section lp-testimonials">
                <div className="lp-wrapper-full">
                    <h2 className="lp-section-title">他们都在用，口碑看得见</h2>

                    <div className="lp-marquee-container">
                        <div className="lp-marquee-track">
                            {/* Double the list for seamless scrolling */}
                            {[...testimonials, ...testimonials].map((item, idx) => (
                                <TestimonialCard
                                    key={idx}
                                    quote={item.quote}
                                    author={item.author}
                                    icon={item.icon}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* CTA Footer */}
            <section className="lp-cta-footer">
                <div className="lp-wrapper">
                    <div className="lp-cta-split">
                        <div className="lp-cta-card lg-card-glass">
                            <h3>个人/团队快速上手</h3>
                            <p>立即开始体验智能审核，提升效率。</p>
                            <button className="lp-btn lp-btn-primary lp-btn-xl" onClick={handleTryIt}>免费使用</button>
                        </div>

                        <div className="lp-cta-card lg-card-glass lp-cta-enterprise">
                            <h3>企业级定制服务</h3>
                            <div className="lp-cta-benefits-list">
                                <span><CheckmarkCircleRegular /> 链接内部数据库</span>
                                <span><CheckmarkCircleRegular /> 私有化部署</span>
                                <span><CheckmarkCircleRegular /> 7×24 技术支持</span>
                            </div>
                            <button className="lp-btn lp-btn-outline lp-btn-xl">申请企业版</button>
                        </div>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="lp-footer">
                <div className="lp-wrapper lp-footer-content">
                    <div className="lp-footer-left">
                        <span>产品简介</span>
                        <span>隐私政策</span>
                        <span>服务条款</span>
                        <span>联系我们</span>
                    </div>
                    <div className="lp-footer-right">
                        &copy; {new Date().getFullYear()} AI Document Review. All rights reserved.
                    </div>
                </div>
            </footer>
        </div>
    );
}

function PainCard({ role, pain, solve, spriteClass }: { role: string, pain: string, solve: string, spriteClass?: string }) {
    return (
        <div className="lp-pain-card">
            {spriteClass && <div className={`lp-pain-icon ${spriteClass}`}></div>}
            <div className="lp-pain-text">
                <div className="lp-pain-role">{role}</div>
                <div className="lp-pain-problem">
                    <span className="lp-icon-cross">✕</span> {pain}
                </div>
                <div className="lp-pain-solution">
                    <span className="lp-icon-check">✓</span> {solve}
                </div>
            </div>
        </div>
    )
}


function TestimonialCard({ quote, author, icon }: { quote: string, author: string, icon: React.ReactNode }) {
    return (
        <div className="lp-test-card">
            <div className="lp-quote">“{quote}”</div>
            <div className="lp-author">
                <span className="lp-author-icon">{icon}</span>
                {author}
            </div>
        </div>
    )
}
