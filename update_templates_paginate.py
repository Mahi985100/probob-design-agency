import re
import os

TEMPLATES_DIR = 'templates'

replacements = [
    {
        'file': 'admin_services.html',
        'var': 'services',
        'route': 'admin_services_page'
    },
    {
        'file': 'admin_portfolio.html',
        'var': 'portfolio_items',
        'route': 'admin_portfolio_page'
    },
    {
        'file': 'admin_blog.html',
        'var': 'blog_posts',
        'route': 'admin_blog_page'
    },
    {
        'file': 'admin_projects.html',
        'var': 'projects',
        'route': 'admin_projects_page'
    },
    {
        'file': 'admin_invoices.html',
        'var': 'invoices',
        'route': 'admin_invoices_page'
    },
    {
        'file': 'admin_billing.html',
        'var': 'payments',
        'route': 'admin_billing_page'
    },
    {
        'file': 'admin_assets.html',
        'var': 'files',
        'route': 'admin_assets_page'
    },
    {
        'file': 'admin_contact.html',
        'var': 'contacts',
        'route': 'admin_contact_page'
    },
    {
        'file': 'admin_activity.html',
        'var': 'logs',
        'route': 'admin_activity_page'
    }
]

for req in replacements:
    filepath = os.path.join(TEMPLATES_DIR, req['file'])
    if not os.path.exists(filepath):
        print(f"Skipping {req['file']} - not found")
        continue

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Change "for item in VAR" to "for item in VAR['items']"
    # Note: we need to handle variations in the loop variable (e.g. `item`, `p`, `inv`, etc.)
    # The pattern is `{% for (.*?) in VAR %}` -> `{% for \1 in VAR['items'] %}`
    pattern = r"\{%\s*for\s+([a-zA-Z0-9_]+)\s+in\s+" + req['var'] + r"\s*%\}"
    replacement = r"{% for \1 in " + req['var'] + "['items'] %}"
    
    # We must only replace it if it hasn't been replaced yet
    if "['items']" not in content and re.search(pattern, content):
        content = re.sub(pattern, replacement, content)

        # Append pagination HTML after `</tbody></table></div>`
        pagination_html = f"""
  <div class="pagination">
    {{% if {req['var']}['has_prev'] %}}<a href="{{{{ url_for('{req['route']}', page={req['var']}['prev_page']) }}}}">Prev</a>{{% endif %}}
    <span>Page {{{{ {req['var']}['page'] }}}} / {{{{ {req['var']}['pages'] }}}}</span>
    {{% if {req['var']}['has_next'] %}}<a href="{{{{ url_for('{req['route']}', page={req['var']}['next_page']) }}}}">Next</a>{{% endif %}}
  </div>
"""
        # Find `</tbody></table></div>` or similar depending on the file
        if "</tbody></table></div>" in content:
            content = content.replace("</tbody></table></div>", "</tbody></table></div>" + pagination_html)
        elif "</tbody>\n      </table>\n    </div>" in content:
            content = content.replace("</tbody>\n      </table>\n    </div>", "</tbody>\n      </table>\n    </div>" + pagination_html)
        elif "</table>\n  </div>" in content:
            content = content.replace("</table>\n  </div>", "</table>\n  </div>" + pagination_html)
        elif "</table></div>" in content:
            content = content.replace("</table></div>", "</table></div>" + pagination_html)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {req['file']}")
    else:
        print(f"Skipped updating {req['file']} (no match or already updated)")

