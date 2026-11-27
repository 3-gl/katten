/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "MarkdownRenderer.h"

#include <QGuiApplication>
#include <QTest>

class MarkdownRendererTest : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void testPlainTextAndEscaping();
    void testHeadings();
    void testInlineFormatting();
    void testLinks();
    void testCodeBlock();
    void testLists();
    void testNestedLists();
    void testTable();
    void testBlockquote();
    void testHorizontalRule();
    void testChart();
};

void MarkdownRendererTest::testPlainTextAndEscaping()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("a < b & c > d"));
    QVERIFY(html.contains(QStringLiteral("a &lt; b &amp; c &gt; d")));
    QVERIFY(!html.contains(QLatin1Char('<') ) || html.contains(QStringLiteral("<p>")));
}

void MarkdownRendererTest::testHeadings()
{
    QCOMPARE(MarkdownRenderer::render(QStringLiteral("# Title")), QStringLiteral("<h1>Title</h1>"));
    QCOMPARE(MarkdownRenderer::render(QStringLiteral("### Sub")), QStringLiteral("<h3>Sub</h3>"));
}

void MarkdownRendererTest::testInlineFormatting()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("This is **bold**, *italic*, ~~gone~~ and `code`."));
    QVERIFY(html.contains(QStringLiteral("<b>bold</b>")));
    QVERIFY(html.contains(QStringLiteral("<i>italic</i>")));
    QVERIFY(html.contains(QStringLiteral("<s>gone</s>")));
    QVERIFY(html.contains(QStringLiteral("<code>code</code>")));
    // No formatting inside code spans.
    const QString codeHtml = MarkdownRenderer::render(QStringLiteral("`**not bold**`"));
    QVERIFY(codeHtml.contains(QStringLiteral("<code>**not bold**</code>")));
    QVERIFY(!codeHtml.contains(QStringLiteral("<b>")));
}

void MarkdownRendererTest::testLinks()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("See [Mistral](https://mistral.ai) and https://example.com/page."));
    QVERIFY(html.contains(QStringLiteral("<a href=\"https://mistral.ai\">Mistral</a>")));
    QVERIFY(html.contains(QStringLiteral("<a href=\"https://example.com/page\">https://example.com/page</a>")));
}

void MarkdownRendererTest::testCodeBlock()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("```python\nprint(\"<hi>\")\n```"));
    QVERIFY(html.contains(QStringLiteral("<pre><code>")));
    QVERIFY(html.contains(QStringLiteral("print(&quot;&lt;hi&gt;&quot;)")));
    QVERIFY(html.contains(QStringLiteral("</code></pre>")));
}

void MarkdownRendererTest::testLists()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("- one\n- two\n\n1. first\n2. second"));
    QVERIFY(html.contains(QStringLiteral("<ul><li>one</li><li>two</li></ul>")));
    QVERIFY(html.contains(QStringLiteral("<ol><li>first</li><li>second</li></ol>")));
}

void MarkdownRendererTest::testNestedLists()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("- a\n  - a1\n  - a2\n- b"));
    QVERIFY(html.contains(QStringLiteral("<li>a</li>")));
    QVERIFY(html.contains(QStringLiteral("<ul><li>a1</li><li>a2</li></ul>")));
    QVERIFY(html.contains(QStringLiteral("<li>b</li>")));
}

void MarkdownRendererTest::testTable()
{
    const QString md = QStringLiteral("| Name | Age |\n| --- | ---: |\n| Ada | 36 |\n| Bob | 41 |");
    const QString html = MarkdownRenderer::render(md);
    QVERIFY(html.contains(QStringLiteral("<table")));
    QVERIFY(html.contains(QStringLiteral("<th style=\"text-align:left\">Name</th>")));
    QVERIFY(html.contains(QStringLiteral("<th style=\"text-align:right\">Age</th>")));
    QVERIFY(html.contains(QStringLiteral("<td style=\"text-align:left\">Ada</td>")));
    QVERIFY(html.contains(QStringLiteral("<td style=\"text-align:right\">36</td>")));
    QVERIFY(html.contains(QStringLiteral("</table>")));
}

void MarkdownRendererTest::testBlockquote()
{
    const QString html = MarkdownRenderer::render(QStringLiteral("> quoted **text**"));
    QVERIFY(html.contains(QStringLiteral("<blockquote>")));
    QVERIFY(html.contains(QStringLiteral("<b>text</b>")));
}

void MarkdownRendererTest::testHorizontalRule()
{
    QVERIFY(MarkdownRenderer::render(QStringLiteral("---")).contains(QStringLiteral("<hr/>")));
}

void MarkdownRendererTest::testChart()
{
    const QString md = QStringLiteral("```chart:bar\n{\"title\": \"Sales\", \"labels\": [\"Q1\", \"Q2\"], \"values\": [3, 7]}\n```");
    const QString html = MarkdownRenderer::render(md);
    QVERIFY(html.contains(QStringLiteral("<img src=\"file://")));
    QVERIFY(html.contains(QStringLiteral(".png\"")));

    const QString csv = MarkdownRenderer::render(QStringLiteral("```chart:line\nQ1, 3\nQ2, 7\n```"));
    QVERIFY(csv.contains(QStringLiteral("<img src=\"file://")));
}

int main(int argc, char **argv)
{
    QGuiApplication app(argc, argv);
    MarkdownRendererTest test;
    return QTest::qExec(&test, argc, argv);
}

#include "markdownrenderertest.moc"
