/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "MarkdownRenderer.h"

#include <QFileInfo>
#include <QGuiApplication>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPainter>
#include <QPalette>
#include <QRegularExpression>
#include <QStandardPaths>
#include <QCryptographicHash>
#include <QDir>
#include <QSvgRenderer>
#include <QUrl>

namespace
{
// QString::replace() with a functor is not available in Qt 6.8; emulate it.
template<typename F>
QString replaceRe(const QString &input, const QRegularExpression &re, F functor)
{
    QString result;
    int pos = 0;
    auto it = re.globalMatch(input);
    while (it.hasNext()) {
        const QRegularExpressionMatch m = it.next();
        result += input.mid(pos, m.capturedStart() - pos);
        result += functor(m);
        pos = m.capturedEnd();
    }
    result += input.mid(pos);
    return result;
}

const QRegularExpression kFenceRe(QStringLiteral("^\\s*```\\s*(\\S*)\\s*$"));
const QRegularExpression kFenceCloseRe(QStringLiteral("^\\s*```\\s*$"));
const QRegularExpression kHeadingRe(QStringLiteral("^\\s{0,3}(#{1,6})\\s+(.*)$"));
const QRegularExpression kHrRe(QStringLiteral("^\\s{0,3}((\\*\\s*){3,}|(-\\s*){3,}|(_\\s*){3,})$"));
const QRegularExpression kListItemRe(QStringLiteral("^(\\s*)([-*+]|\\d+[.)])\\s+(.*)$"));
const QRegularExpression kCodeSpanRe(QStringLiteral("`([^`\\n]+)`"));
const QRegularExpression kImageRe(QStringLiteral("!\\[([^\\]]*)\\]\\(([^)\\s]+)\\)"));
const QRegularExpression kLinkRe(QStringLiteral("\\[([^\\]]+)\\]\\(([^)\\s]+)\\)"));
const QRegularExpression kUrlRe(QStringLiteral("(?<![(\\\"'=])(https?://[^\\s<>\"']+)"));
const QRegularExpression kBoldStarRe(QStringLiteral("\\*\\*([^*]+)\\*\\*"));
const QRegularExpression kBoldUnderscoreRe(QStringLiteral("__([^_]+)__"));
const QRegularExpression kItalicStarRe(QStringLiteral("\\*([^*\\n]+)\\*"));
const QRegularExpression kItalicUnderscoreRe(QStringLiteral("(?<![A-Za-z0-9_])_([^_\\n]+)_(?![A-Za-z0-9_])"));
const QRegularExpression kStrikeRe(QStringLiteral("~~([^~]+)~~"));
const QRegularExpression kCellSepRe(QStringLiteral("^:?-+:?$"));

QStringList splitTableRow(const QString &line)
{
    QString s = line.trimmed();
    if (s.startsWith(QLatin1Char('|')))
        s.remove(0, 1);
    if (s.endsWith(QLatin1Char('|')))
        s.chop(1);
    QStringList cells = s.split(QLatin1Char('|'));
    for (QString &cell : cells)
        cell = cell.trimmed();
    return cells;
}

bool isTableSeparator(const QString &line)
{
    if (!line.contains(QLatin1Char('|')))
        return false;
    const QStringList cells = splitTableRow(line);
    if (cells.isEmpty())
        return false;
    for (const QString &cell : cells) {
        if (!kCellSepRe.match(cell).hasMatch())
            return false;
    }
    return true;
}

bool isBlockStart(const QString &line, const QStringList &lines, int i)
{
    if (kFenceRe.match(line).hasMatch())
        return true;
    if (kHeadingRe.match(line).hasMatch())
        return true;
    if (kHrRe.match(line).hasMatch())
        return true;
    if (line.trimmed().startsWith(QLatin1Char('>')))
        return true;
    if (kListItemRe.match(line).hasMatch())
        return true;
    if (line.contains(QLatin1Char('|')) && i + 1 < lines.size() && isTableSeparator(lines.at(i + 1)))
        return true;
    return false;
}

int indentOf(const QString &line)
{
    int indent = 0;
    for (const QChar c : line) {
        if (c == QLatin1Char(' '))
            ++indent;
        else if (c == QLatin1Char('\t'))
            indent += 4;
        else
            break;
    }
    return indent;
}
} // namespace

QString MarkdownRenderer::renderInline(const QString &text)
{
    // Extract code spans first so no formatting is applied inside them.
    QStringList codeSpans;
    QString working = text;
    working = replaceRe(working, kCodeSpanRe, [&codeSpans](const QRegularExpressionMatch &m) {
        codeSpans.append(m.captured(1));
        return QStringLiteral("\u0001%1\u0002").arg(codeSpans.size() - 1);
    });

    QString s = working.toHtmlEscaped();

    s = replaceRe(s, kImageRe, [](const QRegularExpressionMatch &m) {
        const QString alt = m.captured(1);
        const QString url = m.captured(2);
        QFileInfo info(url);
        if (info.isFile())
            return QStringLiteral("<img src=\"%1\" width=\"480\"/>").arg(QUrl::fromLocalFile(info.absoluteFilePath()).toString());
        return QStringLiteral("<a href=\"%1\">%2</a>").arg(url, alt.isEmpty() ? url : alt);
    });
    s = replaceRe(s, kLinkRe, [](const QRegularExpressionMatch &m) {
        return QStringLiteral("<a href=\"%1\">%2</a>").arg(m.captured(2), m.captured(1));
    });
    {
        // Autolink bare URLs, trimming trailing punctuation.
        QString result;
        int pos = 0;
        auto it = kUrlRe.globalMatch(s);
        while (it.hasNext()) {
            const QRegularExpressionMatch m = it.next();
            QString url = m.captured(1);
            while (!url.isEmpty() && QStringLiteral(".,;:!?)").contains(url.back()))
                url.chop(1);
            result += s.mid(pos, m.capturedStart(1) - pos);
            result += QStringLiteral("<a href=\"%1\">%1</a>").arg(url);
            pos = m.capturedStart(1) + url.length();
        }
        result += s.mid(pos);
        s = result;
    }
    s.replace(kBoldStarRe, QStringLiteral("<b>\\1</b>"));
    s.replace(kBoldUnderscoreRe, QStringLiteral("<b>\\1</b>"));
    s.replace(kStrikeRe, QStringLiteral("<s>\\1</s>"));
    s.replace(kItalicStarRe, QStringLiteral("<i>\\1</i>"));
    s.replace(kItalicUnderscoreRe, QStringLiteral("<i>\\1</i>"));

    // Restore code spans.
    for (int i = 0; i < codeSpans.size(); ++i)
        s.replace(QStringLiteral("\u0001%1\u0002").arg(i), QStringLiteral("<code>%1</code>").arg(codeSpans.at(i).toHtmlEscaped()));

    return s;
}

QString MarkdownRenderer::renderListBlock(const QStringList &lines)
{
    struct Item {
        int indent = 0;
        bool ordered = false;
        QString text;
    };
    QVector<Item> items;
    for (const QString &line : lines) {
        const QRegularExpressionMatch m = kListItemRe.match(line);
        if (m.hasMatch()) {
            const QString marker = m.captured(2);
            Item item;
            item.indent = indentOf(line);
            item.ordered = marker.contains(QRegularExpression(QStringLiteral("\\d")));
            item.text = m.captured(3);
            items.append(item);
        } else if (!items.isEmpty() && !line.trimmed().isEmpty()) {
            items.last().text += QLatin1Char(' ') + line.trimmed();
        }
    }

    QString html;
    QVector<QPair<int, bool>> stack; // indent, ordered
    for (const Item &item : items) {
        while (!stack.isEmpty() && item.indent < stack.last().first) {
            html += stack.last().second ? QStringLiteral("</ol>") : QStringLiteral("</ul>");
            stack.removeLast();
        }
        if (stack.isEmpty() || item.indent > stack.last().first) {
            html += item.ordered ? QStringLiteral("<ol>") : QStringLiteral("<ul>");
            stack.append({item.indent, item.ordered});
        } else if (item.ordered != stack.last().second) {
            html += stack.last().second ? QStringLiteral("</ol>") : QStringLiteral("</ul>");
            html += item.ordered ? QStringLiteral("<ol>") : QStringLiteral("<ul>");
            stack.last().second = item.ordered;
        }
        html += QStringLiteral("<li>%1</li>").arg(renderInline(item.text));
    }
    while (!stack.isEmpty()) {
        html += stack.last().second ? QStringLiteral("</ol>") : QStringLiteral("</ul>");
        stack.removeLast();
    }
    return html;
}

QString MarkdownRenderer::renderTable(const QString &headerLine, const QString &separatorLine, const QStringList &bodyLines)
{
    const QStringList headerCells = splitTableRow(headerLine);
    const QStringList separatorCells = splitTableRow(separatorLine);

    QStringList alignments;
    for (const QString &cell : separatorCells) {
        const QString c = cell.trimmed();
        if (c.startsWith(QLatin1Char(':')) && c.endsWith(QLatin1Char(':')))
            alignments.append(QStringLiteral("center"));
        else if (c.endsWith(QLatin1Char(':')))
            alignments.append(QStringLiteral("right"));
        else
            alignments.append(QStringLiteral("left"));
    }

    auto cellHtml = [](const QString &content, bool header, const QString &align) {
        const QString tag = header ? QStringLiteral("th") : QStringLiteral("td");
        return QStringLiteral("<%1 style=\"text-align:%2\">%3</%1>").arg(tag, align, renderInline(content));
    };

    QString html = QStringLiteral("<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\">");
    html += QStringLiteral("<tr>");
    for (int i = 0; i < headerCells.size(); ++i)
        html += cellHtml(headerCells.at(i), true, i < alignments.size() ? alignments.at(i) : QStringLiteral("left"));
    html += QStringLiteral("</tr>");
    for (const QString &rowLine : bodyLines) {
        const QStringList cells = splitTableRow(rowLine);
        html += QStringLiteral("<tr>");
        for (int i = 0; i < cells.size(); ++i)
            html += cellHtml(cells.at(i), false, i < alignments.size() ? alignments.at(i) : QStringLiteral("left"));
        html += QStringLiteral("</tr>");
    }
    html += QStringLiteral("</table>");
    return html;
}

QString MarkdownRenderer::renderChart(const QString &info, const QString &body)
{
    QString type = info.section(QLatin1Char(':'), 1, 1).toLower();
    if (type.isEmpty())
        type = QStringLiteral("bar");
    if (type != QLatin1String("bar") && type != QLatin1String("line"))
        return QStringLiteral("<pre><code>%1</code></pre>").arg(body.toHtmlEscaped());

    // Parse data: JSON {"title":..., "labels":[...], "values":[...]}, an array of
    // {"label":..,"value":..} objects, or CSV lines "label,value".
    QString title;
    QStringList labels;
    QVector<double> values;

    const QJsonDocument doc = QJsonDocument::fromJson(body.toUtf8());
    if (doc.isObject()) {
        const QJsonObject obj = doc.object();
        title = obj.value(QStringLiteral("title")).toString();
        const QJsonArray labelsArr = obj.value(QStringLiteral("labels")).toArray();
        const QJsonArray valuesArr = obj.value(QStringLiteral("values")).toArray();
        for (const QJsonValue &v : labelsArr)
            labels.append(v.toString());
        for (const QJsonValue &v : valuesArr)
            values.append(v.toDouble());
    } else if (doc.isArray()) {
        for (const QJsonValue &v : doc.array()) {
            const QJsonObject obj = v.toObject();
            labels.append(obj.value(QStringLiteral("label")).toString(obj.value(QStringLiteral("name")).toString()));
            values.append(obj.value(QStringLiteral("value")).toDouble(obj.value(QStringLiteral("y")).toDouble()));
        }
    }
    if (labels.isEmpty() || values.isEmpty()) {
        for (const QString &line : body.split(QLatin1Char('\n'))) {
            const QString trimmed = line.trimmed();
            if (trimmed.isEmpty())
                continue;
            const int comma = trimmed.lastIndexOf(QLatin1Char(','));
            if (comma <= 0)
                continue;
            bool ok = false;
            const double value = trimmed.mid(comma + 1).trimmed().toDouble(&ok);
            if (!ok)
                continue;
            labels.append(trimmed.left(comma).trimmed());
            values.append(value);
        }
    }
    if (labels.isEmpty() || values.isEmpty())
        return QStringLiteral("<pre><code>%1</code></pre>").arg(body.toHtmlEscaped());

    const int count = qMin(labels.size(), values.size());
    double maxValue = 0;
    double minValue = 0;
    for (int i = 0; i < count; ++i) {
        maxValue = qMax(maxValue, values.at(i));
        minValue = qMin(minValue, values.at(i));
    }
    if (maxValue <= minValue)
        maxValue = minValue + 1.0;

    const QPalette palette = QGuiApplication::palette();
    const QString barColor = palette.color(QPalette::Highlight).name();
    const QString textColor = palette.color(QPalette::Text).name();

    const int width = 800;
    const int height = 400;
    const int marginLeft = 70;
    const int marginRight = 30;
    const int marginTop = 50;
    const int marginBottom = 70;
    const int plotWidth = width - marginLeft - marginRight;
    const int plotHeight = height - marginTop - marginBottom;

    QString svg = QStringLiteral("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"%1\" height=\"%2\" viewBox=\"0 0 %1 %2\">")
                      .arg(width)
                      .arg(height);
    svg += QStringLiteral("<rect width=\"100%\" height=\"100%\" fill=\"none\"/>");
    if (!title.isEmpty())
        svg += QStringLiteral("<text x=\"%1\" y=\"28\" font-size=\"18\" fill=\"%2\" text-anchor=\"middle\">%3</text>")
                   .arg(width / 2)
                   .arg(textColor, title.toHtmlEscaped());

    const double range = maxValue - minValue;
    auto yFor = [&](double value) {
        return marginTop + plotHeight * (1.0 - (value - minValue) / range);
    };

    // Axes and gridlines.
    svg += QStringLiteral("<line x1=\"%1\" y1=\"%2\" x2=\"%3\" y2=\"%4\" stroke=\"%5\" stroke-opacity=\"0.5\"/>")
               .arg(marginLeft)
               .arg(marginTop)
               .arg(marginLeft)
               .arg(marginTop + plotHeight)
               .arg(textColor);
    svg += QStringLiteral("<line x1=\"%1\" y1=\"%2\" x2=\"%3\" y2=\"%4\" stroke=\"%5\" stroke-opacity=\"0.5\"/>")
               .arg(marginLeft)
               .arg(marginTop + plotHeight)
               .arg(marginLeft + plotWidth)
               .arg(marginTop + plotHeight)
               .arg(textColor);
    for (int g = 0; g <= 4; ++g) {
        const double value = minValue + range * g / 4.0;
        const int y = int(yFor(value));
        svg += QStringLiteral("<line x1=\"%1\" y1=\"%2\" x2=\"%3\" y2=\"%4\" stroke=\"%5\" stroke-opacity=\"0.15\"/>")
                   .arg(marginLeft)
                   .arg(y)
                   .arg(marginLeft + plotWidth)
                   .arg(y)
                   .arg(textColor);
        svg += QStringLiteral("<text x=\"%1\" y=\"%2\" font-size=\"11\" fill=\"%3\" text-anchor=\"end\">%4</text>")
                   .arg(marginLeft - 6)
                   .arg(y + 4)
                   .arg(textColor)
                   .arg(QString::number(value, 'g', 4));
    }

    if (type == QLatin1String("bar")) {
        const double slot = double(plotWidth) / count;
        const double barWidth = qMax(2.0, slot * 0.7);
        for (int i = 0; i < count; ++i) {
            const double x = marginLeft + slot * i + (slot - barWidth) / 2.0;
            const double y = yFor(qMax(values.at(i), minValue));
            const double h = marginTop + plotHeight - y;
            svg += QStringLiteral("<rect x=\"%1\" y=\"%2\" width=\"%3\" height=\"%4\" fill=\"%5\"/>")
                       .arg(x)
                       .arg(y)
                       .arg(barWidth)
                       .arg(h)
                       .arg(barColor);
            svg += QStringLiteral("<text x=\"%1\" y=\"%2\" font-size=\"11\" fill=\"%3\" text-anchor=\"middle\">%4</text>")
                       .arg(x + barWidth / 2.0)
                       .arg(y - 5)
                       .arg(textColor)
                       .arg(QString::number(values.at(i), 'g', 4));
        }
    } else {
        QString points;
        for (int i = 0; i < count; ++i) {
            const double x = marginLeft + plotWidth * (count == 1 ? 0.5 : double(i) / (count - 1));
            const double y = yFor(values.at(i));
            points += QStringLiteral("%1,%2 ").arg(x).arg(y);
            svg += QStringLiteral("<circle cx=\"%1\" cy=\"%2\" r=\"4\" fill=\"%3\"/>").arg(x).arg(y).arg(barColor);
        }
        svg += QStringLiteral("<polyline points=\"%1\" fill=\"none\" stroke=\"%2\" stroke-width=\"2\"/>").arg(points.trimmed(), barColor);
    }

    // Category labels.
    for (int i = 0; i < count; ++i) {
        QString label = labels.at(i);
        if (label.size() > 14)
            label = label.left(13) + QStringLiteral("…");
        const double lx = type == QLatin1String("bar") ? marginLeft + double(plotWidth) / count * (i + 0.5) : marginLeft + plotWidth * (count == 1 ? 0.5 : double(i) / qMax(1, count - 1));
        svg += QStringLiteral("<text x=\"%1\" y=\"%2\" font-size=\"11\" fill=\"%3\" text-anchor=\"middle\">%4</text>")
                   .arg(lx)
                   .arg(marginTop + plotHeight + 18)
                   .arg(textColor)
                   .arg(label.toHtmlEscaped());
    }
    svg += QStringLiteral("</svg>");

    QSvgRenderer renderer(svg.toUtf8());
    if (!renderer.isValid())
        return QStringLiteral("<pre><code>%1</code></pre>").arg(body.toHtmlEscaped());

    QImage image(width, height, QImage::Format_ARGB32);
    image.fill(Qt::transparent);
    QPainter painter(&image);
    renderer.render(&painter);
    painter.end();

    const QString chartDir = QStandardPaths::writableLocation(QStandardPaths::CacheLocation) + QStringLiteral("/charts");
    QDir().mkpath(chartDir);
    const QString fileName = QString::fromLatin1(QCryptographicHash::hash(svg.toUtf8(), QCryptographicHash::Sha256).toHex()) + QStringLiteral(".png");
    const QString filePath = chartDir + QLatin1Char('/') + fileName;
    if (!QFileInfo::exists(filePath))
        image.save(filePath, "PNG");

    return QStringLiteral("<p><img src=\"%1\" width=\"640\"/></p>").arg(QUrl::fromLocalFile(filePath).toString());
}

QString MarkdownRenderer::render(const QString &markdown)
{
    const QStringList lines = markdown.split(QLatin1Char('\n'));
    QString html;
    int i = 0;
    while (i < lines.size()) {
        const QString line = lines.at(i);
        const QString trimmed = line.trimmed();
        if (trimmed.isEmpty()) {
            ++i;
            continue;
        }

        const QRegularExpressionMatch fence = kFenceRe.match(line);
        if (fence.hasMatch()) {
            const QString info = fence.captured(1);
            QStringList body;
            ++i;
            while (i < lines.size() && !kFenceCloseRe.match(lines.at(i)).hasMatch()) {
                body.append(lines.at(i));
                ++i;
            }
            if (i < lines.size())
                ++i; // skip closing fence
            if (info.startsWith(QLatin1String("chart")))
                html += renderChart(info, body.join(QLatin1Char('\n')));
            else
                html += QStringLiteral("<pre><code>%1</code></pre>").arg(body.join(QLatin1Char('\n')).toHtmlEscaped());
            continue;
        }

        const QRegularExpressionMatch heading = kHeadingRe.match(line);
        if (heading.hasMatch()) {
            const int level = heading.captured(1).size();
            html += QStringLiteral("<h%1>%2</h%1>").arg(level).arg(renderInline(heading.captured(2).trimmed()));
            ++i;
            continue;
        }

        if (kHrRe.match(line).hasMatch()) {
            html += QStringLiteral("<hr/>");
            ++i;
            continue;
        }

        if (trimmed.startsWith(QLatin1Char('>'))) {
            QStringList quoteLines;
            while (i < lines.size() && lines.at(i).trimmed().startsWith(QLatin1Char('>'))) {
                QString q = lines.at(i).trimmed();
                q.remove(0, 1);
                if (q.startsWith(QLatin1Char(' ')))
                    q.remove(0, 1);
                quoteLines.append(q);
                ++i;
            }
            html += QStringLiteral("<blockquote>%1</blockquote>").arg(render(quoteLines.join(QLatin1Char('\n'))));
            continue;
        }

        if (line.contains(QLatin1Char('|')) && i + 1 < lines.size() && isTableSeparator(lines.at(i + 1))) {
            const QString headerLine = line;
            const QString separatorLine = lines.at(i + 1);
            QStringList bodyLines;
            i += 2;
            while (i < lines.size() && lines.at(i).contains(QLatin1Char('|')) && !lines.at(i).trimmed().isEmpty()) {
                bodyLines.append(lines.at(i));
                ++i;
            }
            html += renderTable(headerLine, separatorLine, bodyLines);
            continue;
        }

        if (kListItemRe.match(line).hasMatch()) {
            QStringList listLines;
            const int baseIndent = indentOf(line);
            while (i < lines.size()) {
                const QString l = lines.at(i);
                if (l.trimmed().isEmpty()) {
                    // Include the blank line only if the list continues after it.
                    int j = i + 1;
                    while (j < lines.size() && lines.at(j).trimmed().isEmpty())
                        ++j;
                    if (j < lines.size() && kListItemRe.match(lines.at(j)).hasMatch() && indentOf(lines.at(j)) >= baseIndent) {
                        listLines.append(l);
                        ++i;
                        continue;
                    }
                    break;
                }
                if (kListItemRe.match(l).hasMatch() || indentOf(l) > baseIndent) {
                    listLines.append(l);
                    ++i;
                    continue;
                }
                break;
            }
            html += renderListBlock(listLines);
            continue;
        }

        // Paragraph.
        QStringList paragraphLines;
        while (i < lines.size() && !lines.at(i).trimmed().isEmpty() && !isBlockStart(lines.at(i), lines, i)) {
            paragraphLines.append(lines.at(i).trimmed());
            ++i;
        }
        html += QStringLiteral("<p>%1</p>").arg(renderInline(paragraphLines.join(QLatin1Char(' '))));
    }
    return html;
}
